"""
QEMU Guest Agent Wrapper
========================
A Python wrapper for communicating with QEMU Guest Agent via Unix socket.

This module provides both low-level socket communication (QGAConnection) and
high-level API (QGAClient) for executing commands and managing the guest VM.
"""

import socket
import json
import base64
import time
import logging
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QGAError(Exception):
    """Base exception for QGA-related errors."""
    pass


class QGAConnectionError(QGAError):
    """Exception raised for socket connection errors."""
    pass


class QGAProtocolError(QGAError):
    """Exception raised for QGA protocol errors."""
    pass


class QGAConnection:
    """
    Low-level socket communication handler for QEMU Guest Agent.
    
    Handles Unix socket connection, JSON-RPC request/response formatting,
    and basic error handling.
    """
    
    def __init__(self, socket_path: str, timeout: int = 30):
        """
        Initialize QGA connection.
        
        Args:
            socket_path: Path to the Unix socket (e.g., /tmp/qga.sock)
            timeout: Socket timeout in seconds
        """
        self.socket_path = socket_path
        self.timeout = timeout
        self._sock = None
        
    def connect(self):
        """Establish connection to the Unix socket."""
        try:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect(self.socket_path)
            logger.info(f"Connected to QGA at {self.socket_path}")
        except socket.error as e:
            raise QGAConnectionError(f"Failed to connect to {self.socket_path}: {e}")
    
    def disconnect(self):
        """Close the socket connection."""
        if self._sock:
            self._sock.close()
            self._sock = None
            logger.info("Disconnected from QGA")
    
    def send_command(self, command: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC command to QGA and return the response.
        
        Args:
            command: QGA command name (e.g., 'guest-ping', 'guest-exec')
            arguments: Optional dictionary of command arguments
            
        Returns:
            Dictionary containing the response from QGA
            
        Raises:
            QGAConnectionError: If not connected or socket error occurs
            QGAProtocolError: If QGA returns an error response
        """
        if not self._sock:
            raise QGAConnectionError("Not connected to QGA socket")
        
        # Build JSON-RPC request
        request = {"execute": command}
        if arguments:
            request["arguments"] = arguments
        
        # Serialize and send
        request_json = json.dumps(request) + "\n"
        logger.debug(f"Sending command: {request_json.strip()}")
        
        try:
            self._sock.sendall(request_json.encode('utf-8'))
        except socket.error as e:
            raise QGAConnectionError(f"Failed to send command: {e}")
        
        # Receive response
        response_data = b""
        try:
            # QGA responses are typically small and complete in one or few reads
            while True:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                
                # Try to parse as JSON - if successful, we have a complete response
                try:
                    json.loads(response_data.decode('utf-8'))
                    # Successfully parsed, we have complete JSON
                    break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Not complete yet, continue reading
                    # But check if we've received something that looks like an end
                    if b'\n' in response_data or response_data.endswith(b'}'):
                        # Give it one more small read attempt or break
                        self._sock.settimeout(0.1)  # Very short timeout for next chunk
                        try:
                            extra = self._sock.recv(1024)
                            if extra:
                                response_data += extra
                            else:
                                break
                        except socket.timeout:
                            # No more data, what we have is complete
                            break
                        finally:
                            self._sock.settimeout(self.timeout)  # Restore timeout
                    continue
        except socket.timeout:
            raise QGAConnectionError("Timeout waiting for response")
        except socket.error as e:
            raise QGAConnectionError(f"Failed to receive response: {e}")
        
        # Parse response
        try:
            response = json.loads(response_data.decode('utf-8'))
            logger.debug(f"Received response: {response}")
        except json.JSONDecodeError as e:
            raise QGAProtocolError(f"Invalid JSON response: {e}")
        
        # Check for error response
        if "error" in response:
            error_msg = response["error"].get("desc", "Unknown error")
            raise QGAProtocolError(f"QGA error: {error_msg}")
        
        return response
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class QGAClient:
    """
    High-level API for QEMU Guest Agent operations.
    
    Provides convenient methods for common QGA operations, handling
    async command execution patterns and data encoding/decoding.
    """
    
    def __init__(self, socket_path: str = "/tmp/qga.sock", timeout: int = 30,
                 poll_interval: float = 0.1, max_poll_retries: int = 300):
        """
        Initialize QGA client.
        
        Args:
            socket_path: Path to the Unix socket
            timeout: Socket timeout in seconds
            poll_interval: Time between status polls in seconds
            max_poll_retries: Maximum number of polling attempts
        """
        self.socket_path = socket_path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_poll_retries = max_poll_retries
        self._connection = None
    
    def connect(self):
        """Establish connection to QGA."""
        self._connection = QGAConnection(self.socket_path, self.timeout)
        self._connection.connect()
    
    def disconnect(self):
        """Close connection to QGA."""
        if self._connection:
            self._connection.disconnect()
            self._connection = None
    
    def _ensure_connected(self):
        """Ensure we have an active connection."""
        if not self._connection:
            self.connect()
    
    # ===== Basic Commands =====
    
    def ping(self) -> bool:
        """
        Ping the guest agent to check connectivity.
        
        Returns:
            True if ping successful
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-ping")
        return "return" in response
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the guest agent.
        
        Returns:
            Dictionary with version and supported commands
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-info")
        return response.get("return", {})
    
    def get_osinfo(self) -> Dict[str, Any]:
        """
        Get operating system information.
        
        Returns:
            Dictionary with OS name, version, kernel, etc.
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-get-osinfo")
        return response.get("return", {})
    
    def get_hostname(self) -> str:
        """
        Get the guest's hostname.
        
        Returns:
            Hostname string
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-get-host-name")
        return response.get("return", {}).get("host-name", "")
    
    def get_users(self) -> List[Dict[str, Any]]:
        """
        Get list of logged-in users.
        
        Returns:
            List of user dictionaries
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-get-users")
        return response.get("return", [])
    
    def get_timezone(self) -> Dict[str, Any]:
        """
        Get timezone information.
        
        Returns:
            Dictionary with timezone info
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-get-timezone")
        return response.get("return", {})
    
    # ===== Command Execution =====
    
    def exec_command(self, command: List[str], capture_output: bool = True,
                    input_data: Optional[str] = None, env: Optional[List[str]] = None) -> int:
        """
        Execute a command in the guest (async - returns PID).
        
        Args:
            command: List of command and arguments (e.g., ['ls', '-la'])
            capture_output: Whether to capture stdout/stderr
            input_data: Optional input data to pass to command
            env: Optional environment variables
            
        Returns:
            Process ID (PID) for status polling
        """
        self._ensure_connected()
        
        arguments = {
            "path": command[0],
            "capture-output": capture_output
        }
        
        if len(command) > 1:
            arguments["arg"] = command[1:]
        
        if input_data:
            arguments["input-data"] = base64.b64encode(input_data.encode()).decode()
        
        if env:
            arguments["env"] = env
        
        response = self._connection.send_command("guest-exec", arguments)
        return response.get("return", {}).get("pid")
    
    def get_exec_status(self, pid: int) -> Dict[str, Any]:
        """
        Get status of a previously executed command.
        
        Args:
            pid: Process ID returned by exec_command
            
        Returns:
            Dictionary with execution status, output, and exit code
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-exec-status", {"pid": pid})
        return response.get("return", {})
    
    def run_command(self, command: List[str], capture_output: bool = True,
                   input_data: Optional[str] = None, env: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute a command and wait for completion (synchronous wrapper).
        
        Args:
            command: List of command and arguments
            capture_output: Whether to capture stdout/stderr
            input_data: Optional input data
            env: Optional environment variables
            
        Returns:
            Dictionary with:
                - exitcode: Exit code of the command
                - stdout: Standard output (decoded)
                - stderr: Standard error (decoded)
                - exited: Boolean indicating completion
        """
        # Execute command
        pid = self.exec_command(command, capture_output, input_data, env)
        logger.info(f"Executing command: {' '.join(command)} (PID: {pid})")
        
        # Poll for completion
        retries = 0
        while retries < self.max_poll_retries:
            status = self.get_exec_status(pid)
            
            if status.get("exited", False):
                # Command completed
                result = {
                    "exitcode": status.get("exitcode", -1),
                    "exited": True,
                    "stdout": "",
                    "stderr": ""
                }
                
                # Decode output if present
                if "out-data" in status:
                    try:
                        result["stdout"] = base64.b64decode(status["out-data"]).decode('utf-8')
                    except Exception as e:
                        logger.warning(f"Failed to decode stdout: {e}")
                
                if "err-data" in status:
                    try:
                        result["stderr"] = base64.b64decode(status["err-data"]).decode('utf-8')
                    except Exception as e:
                        logger.warning(f"Failed to decode stderr: {e}")
                
                logger.info(f"Command completed with exit code: {result['exitcode']}")
                return result
            
            time.sleep(self.poll_interval)
            retries += 1
        
        raise QGAError(f"Command execution timeout after {retries * self.poll_interval} seconds")
    
    # ===== User Management =====
    
    def set_user_password(self, username: str, password: str, crypted: bool = False) -> bool:
        """
        Set or change a user's password.
        
        Args:
            username: Username to change password for
            password: New password (will be base64 encoded)
            crypted: Whether the password is already crypted
            
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        # Encode password in base64
        password_b64 = base64.b64encode(password.encode()).decode()
        
        arguments = {
            "username": username,
            "password": password_b64,
            "crypted": crypted
        }
        
        response = self._connection.send_command("guest-set-user-password", arguments)
        logger.info(f"Password changed for user: {username}")
        return "return" in response
    
    # ===== Network Information =====
    
    def get_network_interfaces(self) -> List[Dict[str, Any]]:
        """
        Get network interface information.
        
        Returns:
            List of network interface dictionaries
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-network-get-interfaces")
        return response.get("return", [])
    
    # ===== Filesystem Operations =====
    
    def get_fsinfo(self) -> List[Dict[str, Any]]:
        """
        Get filesystem information.
        
        Returns:
            List of filesystem mount points and details
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-get-fsinfo")
        return response.get("return", [])
    
    def fsfreeze(self, mountpoints: Optional[List[str]] = None) -> int:
        """
        Freeze filesystems.
        
        Args:
            mountpoints: Optional list of specific mountpoints to freeze
            
        Returns:
            Number of filesystems frozen
        """
        self._ensure_connected()
        
        if mountpoints:
            arguments = {"mountpoints": mountpoints}
            response = self._connection.send_command("guest-fsfreeze-freeze-list", arguments)
        else:
            response = self._connection.send_command("guest-fsfreeze-freeze")
        
        return response.get("return", 0)
    
    def fsthaw(self) -> int:
        """
        Thaw (unfreeze) filesystems.
        
        Returns:
            Number of filesystems thawed
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-fsfreeze-thaw")
        return response.get("return", 0)
    
    def fsfreeze_status(self) -> str:
        """
        Get filesystem freeze status.
        
        Returns:
            Status string ('frozen' or 'thawed')
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-fsfreeze-status")
        return response.get("return", "")
    
    # ===== SSH Key Management =====
    
    def ssh_get_authorized_keys(self, username: str) -> List[str]:
        """
        Get authorized SSH keys for a user.
        
        Args:
            username: Username to get keys for
            
        Returns:
            List of SSH public keys
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-ssh-get-authorized-keys", 
                                                {"username": username})
        keys_data = response.get("return", {}).get("keys", [])
        return [key.get("key", "") for key in keys_data]
    
    def ssh_add_authorized_keys(self, username: str, keys: List[str], reset: bool = False):
        """
        Add SSH authorized keys for a user.
        
        Args:
            username: Username to add keys for
            keys: List of SSH public keys to add
            reset: If True, replace all existing keys
        """
        self._ensure_connected()
        
        keys_list = [{"key": key} for key in keys]
        arguments = {
            "username": username,
            "keys": keys_list,
            "reset": reset
        }
        
        self._connection.send_command("guest-ssh-add-authorized-keys", arguments)
        logger.info(f"Added {len(keys)} SSH key(s) for user: {username}")
    
    def ssh_remove_authorized_keys(self, username: str, keys: List[str]):
        """
        Remove SSH authorized keys for a user.
        
        Args:
            username: Username to remove keys from
            keys: List of SSH public keys to remove
        """
        self._ensure_connected()
        
        keys_list = [{"key": key} for key in keys]
        arguments = {
            "username": username,
            "keys": keys_list
        }
        
        self._connection.send_command("guest-ssh-remove-authorized-keys", arguments)
        logger.info(f"Removed {len(keys)} SSH key(s) for user: {username}")
    
    # ===== File Operations =====
    
    def file_open(self, path: str, mode: str = "r") -> int:
        """
        Open a file in the guest.
        
        Args:
            path: Path to the file
            mode: Open mode ('r', 'w', 'a', 'r+', 'w+', 'a+')
            
        Returns:
            File handle ID
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-file-open", 
                                                {"path": path, "mode": mode})
        return response.get("return", 0)
    
    def file_close(self, handle: int):
        """
        Close a file in the guest.
        
        Args:
            handle: File handle ID from file_open
        """
        self._ensure_connected()
        self._connection.send_command("guest-file-close", {"handle": handle})
    
    def file_read(self, handle: int, count: int = 4096) -> str:
        """
        Read from a file in the guest.
        
        Args:
            handle: File handle ID
            count: Number of bytes to read
            
        Returns:
            File content (decoded from base64)
        """
        self._ensure_connected()
        response = self._connection.send_command("guest-file-read", 
                                                {"handle": handle, "count": count})
        data = response.get("return", {})
        
        if "buf-b64" in data:
            return base64.b64decode(data["buf-b64"]).decode('utf-8')
        return ""
    
    def file_write(self, handle: int, content: str) -> int:
        """
        Write to a file in the guest.
        
        Args:
            handle: File handle ID
            content: Content to write
            
        Returns:
            Number of bytes written
        """
        self._ensure_connected()
        content_b64 = base64.b64encode(content.encode()).decode()
        response = self._connection.send_command("guest-file-write",
                                                {"handle": handle, "buf-b64": content_b64})
        return response.get("return", {}).get("count", 0)
    
    # ===== System Control =====
    
    def shutdown(self, mode: str = "powerdown"):
        """
        Shutdown or reboot the guest.
        
        Args:
            mode: Shutdown mode ('powerdown', 'reboot', 'halt')
        """
        self._ensure_connected()
        self._connection.send_command("guest-shutdown", {"mode": mode})
        logger.info(f"Initiated guest {mode}")
    
    # ===== Context Manager =====
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


if __name__ == "__main__":
    # Simple test
    with QGAClient() as client:
        print("Testing QGA connection...")
        
        # Test ping
        if client.ping():
            print("✓ Ping successful")
        
        # Get OS info
        osinfo = client.get_osinfo()
        print(f"✓ Guest OS: {osinfo.get('name')} {osinfo.get('version')}")
        
        # Execute a simple command
        result = client.run_command(['uname', '-a'])
        print(f"✓ Command output: {result['stdout'].strip()}")
        print(f"✓ Exit code: {result['exitcode']}")
