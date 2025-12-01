#!/usr/bin/env python3
"""
Example usage of the QEMU Guest Agent Wrapper
==============================================

This script demonstrates various ways to use the QGA wrapper.
"""

import sys
import os

# Add src directory to path to import qga_wrapper
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from qga_wrapper import QGAClient, QGAError


def example_basic_operations():
    """Example: Basic connectivity and information gathering."""
    print("=== Basic Operations ===\n")
    
    with QGAClient() as client:
        # Test connectivity
        if client.ping():
            print("✓ Guest agent is responding\n")
        
        # Get OS information
        osinfo = client.get_osinfo()
        print(f"Operating System: {osinfo.get('name')}")
        print(f"Version: {osinfo.get('version')}")
        print(f"Kernel: {osinfo.get('kernel-release')}\n")
        
        # Get hostname
        hostname = client.get_hostname()
        print(f"Hostname: {hostname}\n")


def example_command_execution():
    """Example: Execute commands in the guest."""
    print("=== Command Execution ===\n")
    
    with QGAClient() as client:
        # Execute a simple command
        result = client.run_command(['whoami'])
        print(f"Current user: {result['stdout'].strip()}")
        
        # Execute with arguments
        result = client.run_command(['ls', '-la', '/home'])
        print(f"\nDirectory listing:\n{result['stdout']}")
        
        # Check exit code
        result = client.run_command(['test', '-f', '/etc/passwd'])
        if result['exitcode'] == 0:
            print("File /etc/passwd exists")


def example_network_info():
    """Example: Get network interface information."""
    print("=== Network Information ===\n")
    
    with QGAClient() as client:
        interfaces = client.get_network_interfaces()
        
        for iface in interfaces:
            print(f"Interface: {iface.get('name')}")
            print(f"  MAC: {iface.get('hardware-address')}")
            
            if 'ip-addresses' in iface:
                print("  IP Addresses:")
                for ip in iface.get('ip-addresses', []):
                    print(f"    - {ip.get('ip-address')} ({ip.get('ip-address-type')})")
            print()


def example_file_operations():
    """Example: File operations in the guest."""
    print("=== File Operations ===\n")
    
    with QGAClient() as client:
        # Write a file
        handle = client.file_open('/tmp/test_qga.txt', 'w')
        bytes_written = client.file_write(handle, 'Hello from QGA wrapper!\n')
        client.file_close(handle)
        print(f"Wrote {bytes_written} bytes to /tmp/test_qga.txt")
        
        # Read the file back
        handle = client.file_open('/tmp/test_qga.txt', 'r')
        content = client.file_read(handle)
        client.file_close(handle)
        print(f"Read content: {content}")


def example_user_management():
    """Example: User management (commented out for safety)."""
    print("=== User Management ===\n")
    
    # CAUTION: This will actually change the password!
    # Uncomment only if you want to test this functionality
    
    print("Password management example (commented out for safety)")
    print("To use: client.set_user_password('username', 'newpassword')")
    
    # with QGAClient() as client:
    #     # Change password for a user
    #     client.set_user_password('testuser', 'newpassword123')
    #     print("Password updated successfully")


def example_async_execution():
    """Example: Async command execution pattern."""
    print("=== Async Command Execution ===\n")
    
    with QGAClient() as client:
        # Launch command asynchronously
        pid = client.exec_command(['sleep', '2'])
        print(f"Launched command with PID: {pid}")
        
        # You can do other work here...
        print("Doing other work while command runs...")
        
        # Poll for completion
        import time
        while True:
            status = client.get_exec_status(pid)
            if status.get('exited'):
                print(f"Command completed with exit code: {status.get('exitcode')}")
                break
            time.sleep(0.1)


def example_error_handling():
    """Example: Error handling."""
    print("=== Error Handling ===\n")
    
    try:
        with QGAClient() as client:
            # Try to execute a non-existent command
            result = client.run_command(['nonexistent_command'])
    except QGAError as e:
        print(f"Caught expected error: {e}")
    
    print("Error handling works correctly!")


def example_reusing_connection():
    """Example: Reusing connection for multiple operations."""
    print("=== Reusing Connection ===\n")
    
    client = QGAClient()
    client.connect()
    
    try:
        # Multiple operations with same connection
        for i in range(3):
            result = client.run_command(['echo', f'Message {i+1}'])
            print(f"{i+1}. {result['stdout'].strip()}")
    finally:
        client.disconnect()


def main():
    """Run all examples."""
    print("QEMU Guest Agent Wrapper - Usage Examples")
    print("=" * 50)
    print()
    
    try:
        example_basic_operations()
        example_command_execution()
        example_network_info()
        example_file_operations()
        example_user_management()
        example_async_execution()
        example_error_handling()
        example_reusing_connection()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except QGAError as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("1. The QEMU VM is running")
        print("2. qemu-guest-agent is installed and running in the guest")
        print("3. The socket path is correct (/tmp/qga.sock)")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
