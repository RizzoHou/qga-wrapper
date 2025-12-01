# QEMU Guest Agent Wrapper - Development Notes

This document provides detailed explanations of the implementation, key concepts, and design decisions made during the development of the QGA wrapper.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Communication Protocol](#communication-protocol)
5. [Async Command Execution](#async-command-execution)
6. [Error Handling](#error-handling)
7. [Extending the Wrapper](#extending-the-wrapper)
8. [Testing & Debugging](#testing--debugging)

## Overview

The QEMU Guest Agent (QGA) wrapper is a Python tool that enables host-to-guest communication for QEMU/KVM virtual machines. It abstracts the low-level JSON-RPC protocol used by QGA into a user-friendly Python API and CLI.

### Design Goals

1. **Simplicity**: Easy to use for common operations
2. **Extensibility**: Simple to add support for new QGA commands
3. **Robustness**: Proper error handling and timeout management
4. **Completeness**: Support for the full range of QGA operations

## Architecture

The wrapper follows a layered architecture:

```
┌─────────────────────────────────────────┐
│         CLI Interface (src/qga)          │
│  User-facing command-line tool          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      High-Level API (QGAClient)          │
│  - Convenient methods for operations     │
│  - Async command execution handling      │
│  - Data encoding/decoding                │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│   Low-Level Comm (QGAConnection)         │
│  - Socket management                     │
│  - JSON-RPC protocol handling            │
│  - Basic error checking                  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Unix Socket (/tmp/qga.sock)      │
│         QEMU Guest Agent                 │
└──────────────────────────────────────────┘
```

## Core Components

### 1. QGAConnection (Low-Level Layer)

**Purpose**: Handles Unix socket communication and JSON-RPC protocol

**Key Responsibilities**:
- Establishing and managing socket connections
- Serializing commands to JSON-RPC format
- Deserializing responses from JSON
- Basic error detection (connection errors, JSON parsing errors)

**Implementation Details**:

```python
class QGAConnection:
    def __init__(self, socket_path: str, timeout: int = 30):
        self.socket_path = socket_path
        self.timeout = timeout
        self._sock = None
```

The connection is lazy - it doesn't connect until `connect()` is called. This allows for flexible usage patterns.

**JSON-RPC Protocol**:

QGA uses JSON-RPC 1.0 format:

Request:
```json
{"execute": "guest-ping"}
```

Response:
```json
{"return": {}}
```

Error Response:
```json
{"error": {"class": "CommandNotFound", "desc": "..."}}
```

**Socket Communication Strategy**:

The response reading logic is critical and handles several edge cases:

1. **Complete Response Detection**: We read chunks and try to parse as JSON. If successful, we have a complete response.
2. **Partial Response Handling**: If JSON parsing fails, we continue reading.
3. **End Detection**: We look for newlines or closing braces as hints that more data might not be coming.
4. **Graceful Timeout**: A short timeout on the final read attempt ensures we don't wait forever.

```python
# Try to parse as JSON - if successful, we have a complete response
try:
    json.loads(response_data.decode('utf-8'))
    break  # Successfully parsed, we have complete JSON
except (json.JSONDecodeError, UnicodeDecodeError):
    # Not complete yet, continue reading
    continue
```

### 2. QGAClient (High-Level Layer)

**Purpose**: Provides convenient Python methods for QGA operations

**Key Responsibilities**:
- Managing connection lifecycle
- Implementing async command execution pattern
- Encoding/decoding data (Base64)
- Polling for command completion
- Error handling and retry logic

**Connection Management**:

The `_ensure_connected()` pattern allows methods to be called without explicitly connecting first:

```python
def _ensure_connected(self):
    if not self._connection:
        self.connect()
```

**Context Manager Support**:

Both `QGAConnection` and `QGAClient` support context managers for automatic resource cleanup:

```python
with QGAClient() as client:
    client.ping()
# Automatically disconnects
```

### 3. CLI Interface (src/qga)

**Purpose**: Command-line interface for end users

**Key Features**:
- Argument parsing with argparse
- Multiple output formats (text, JSON)
- Proper exit codes
- User-friendly error messages

**Command Pattern**:

Each CLI command has a dedicated handler function:

```python
def cmd_ping(client, args):
    """Test connectivity to guest agent."""
    if client.ping():
        print("✓ Guest agent is responding")
        return 0
    return 1
```

## Communication Protocol

### JSON-RPC Format

QGA uses a simplified JSON-RPC protocol. Every request has this format:

```json
{
  "execute": "command-name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

The `arguments` field is optional and only included when the command requires parameters.

### Base64 Encoding

Several QGA commands use Base64 encoding for data:

1. **Password Setting**: Passwords must be Base64 encoded
2. **Command Input**: Input data for `guest-exec` is Base64 encoded
3. **Command Output**: stdout/stderr from `guest-exec` is Base64 encoded
4. **File Operations**: File content is Base64 encoded

Example:
```python
# Encoding
password_b64 = base64.b64encode(password.encode()).decode()

# Decoding
output = base64.b64decode(status["out-data"]).decode('utf-8')
```

## Async Command Execution

One of the most important patterns in the wrapper is handling asynchronous command execution.

### The Challenge

`guest-exec` doesn't wait for command completion. Instead:
1. It launches the command
2. Returns a PID immediately
3. You must poll `guest-exec-status` with the PID to get results

### The Solution

The `run_command()` method wraps this async pattern into a synchronous interface:

```python
def run_command(self, command: List[str]) -> Dict[str, Any]:
    # Step 1: Launch command
    pid = self.exec_command(command)
    
    # Step 2: Poll for completion
    retries = 0
    while retries < self.max_poll_retries:
        status = self.get_exec_status(pid)
        
        if status.get("exited", False):
            # Step 3: Decode and return results
            result = {
                "exitcode": status.get("exitcode", -1),
                "stdout": base64.b64decode(status["out-data"]).decode(),
                "stderr": base64.b64decode(status["err-data"]).decode(),
            }
            return result
        
        time.sleep(self.poll_interval)
        retries += 1
    
    raise QGAError("Timeout")
```

### Polling Configuration

The polling behavior is configurable:

- `poll_interval`: Time between checks (default: 0.1s)
- `max_poll_retries`: Maximum attempts (default: 300)

With defaults, the maximum wait time is 30 seconds (300 × 0.1s).

## Error Handling

The wrapper uses a hierarchy of custom exceptions:

```
QGAError (base)
├── QGAConnectionError (socket/connection issues)
└── QGAProtocolError (protocol/response errors)
```

### Error Handling Strategy

1. **Connection Errors**: Raised when socket operations fail
   ```python
   except socket.error as e:
       raise QGAConnectionError(f"Failed to connect: {e}")
   ```

2. **Protocol Errors**: Raised when QGA returns an error
   ```python
   if "error" in response:
       raise QGAProtocolError(f"QGA error: {error_msg}")
   ```

3. **Timeout Errors**: Raised when operations take too long
   ```python
   if retries >= self.max_poll_retries:
       raise QGAError("Timeout")
   ```

### CLI Error Handling

The CLI catches exceptions and provides user-friendly messages:

```python
except QGAConnectionError as e:
    print(f"Connection error: {e}", file=sys.stderr)
    print("\nIs the QEMU VM running with QGA enabled?", file=sys.stderr)
    return 1
```

## Extending the Wrapper

Adding support for a new QGA command is straightforward.

### Step 1: Add Method to QGAClient

```python
def my_new_command(self, param1: str, param2: int) -> Dict[str, Any]:
    """
    Description of what this command does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Dictionary containing the result
    """
    self._ensure_connected()
    
    arguments = {
        "param1": param1,
        "param2": param2
    }
    
    response = self._connection.send_command("guest-my-command", arguments)
    return response.get("return", {})
```

### Step 2: Add CLI Command (Optional)

```python
def cmd_my_command(client, args):
    """Handle my-command CLI."""
    result = client.my_new_command(args.param1, args.param2)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Result: {result}")
    
    return 0

# Add to parser
my_parser = subparsers.add_parser('my-command', help='Do something')
my_parser.add_argument('param1', help='First parameter')
my_parser.add_argument('param2', type=int, help='Second parameter')

# Register handler
commands['my-command'] = cmd_my_command
```

### Example: Adding CPU Stats Command

Let's walk through adding `guest-get-cpustats`:

**1. Add to QGAClient:**
```python
def get_cpustats(self) -> List[Dict[str, Any]]:
    """
    Get CPU statistics.
    
    Returns:
        List of CPU statistics dictionaries
    """
    self._ensure_connected()
    response = self._connection.send_command("guest-get-cpustats")
    return response.get("return", [])
```

**2. Add CLI command:**
```python
def cmd_cpustats(client, args):
    """Get CPU statistics."""
    stats = client.get_cpustats()
    
    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"CPU Statistics ({len(stats)} CPUs):")
        for i, cpu in enumerate(stats):
            print(f"\n  CPU {i}:")
            for key, value in cpu.items():
                print(f"    {key}: {value}")
    
    return 0

# Register
subparsers.add_parser('cpustats', help='Get CPU statistics')
commands['cpustats'] = cmd_cpustats
```

**3. Test:**
```bash
python src/qga cpustats
python src/qga -j cpustats
```

## Testing & Debugging

### Manual Testing

The simplest way to test is using the built-in test in `qga_wrapper.py`:

```bash
source venv/bin/activate
python qga_wrapper.py
```

### CLI Testing

Test individual commands:

```bash
# Connectivity
python src/qga ping

# Information gathering
python src/qga osinfo
python src/qga hostname
python src/qga network

# Command execution
python src/qga exec whoami
python src/qga exec uname -a

# JSON output
python src/qga -j osinfo
```

### Debugging Tips

**1. Enable Debug Logging:**

Modify the logging level in `qga_wrapper.py`:

```python
logging.basicConfig(level=logging.DEBUG, ...)
```

This shows all JSON-RPC requests and responses.

**2. Check Socket:**

Verify the socket exists and is accessible:

```bash
ls -la /tmp/qga.sock
```

**3. Test with socat:**

You can test QGA directly with socat:

```bash
echo '{"execute":"guest-ping"}' | socat - UNIX-CONNECT:/tmp/qga.sock
```

**4. Check Guest Agent:**

Inside the VM, verify the agent is running:

```bash
sudo systemctl status qemu-guest-agent
sudo journalctl -u qemu-guest-agent
```

### Common Issues

**Connection Refused**:
- VM not running
- Socket path incorrect
- Another process holding the socket

**Timeout on Command Execution**:
- Command takes longer than poll timeout
- Increase timeout: `QGAClient(timeout=60)`
- Or increase max retries: `QGAClient(max_poll_retries=600)`

**Base64 Decode Errors**:
- QGA version mismatch
- Command output contains binary data
- Try different encoding or handle as bytes

## Performance Considerations

### Connection Pooling

For repeated operations, reuse the connection:

```python
# Good - reuses connection
client = QGAClient()
client.connect()
for i in range(100):
    result = client.run_command(['echo', f'test{i}'])
client.disconnect()

# Less efficient - reconnects each time
for i in range(100):
    with QGAClient() as client:
        result = client.run_command(['echo', f'test{i}'])
```

### Polling Optimization

Adjust polling based on expected command duration:

```python
# Quick commands - short interval
client = QGAClient(poll_interval=0.05)

# Long-running commands - longer interval
client = QGAClient(poll_interval=0.5, max_poll_retries=600)
```

## Security Considerations

1. **Password Handling**: Passwords are Base64 encoded (not encrypted). Use secure channels.
2. **Command Injection**: Be careful with user input in `exec` commands
3. **File Access**: File operations have guest VM permissions
4. **Socket Permissions**: Ensure proper permissions on the socket file

## Future Enhancements

Possible improvements:

1. **Async API**: Use Python's asyncio for truly async operations
2. **Command Queuing**: Queue multiple commands for batch execution
3. **Event Notifications**: React to guest events
4. **Configuration File**: Support for loading socket path from config
5. **Shell Completion**: Bash/Zsh completion scripts
6. **More Commands**: Support for all 42 QGA commands
7. **Retry Logic**: Automatic retry on transient failures
8. **Connection Pool**: Manage multiple VM connections

## Conclusion

This wrapper demonstrates clean separation of concerns, proper error handling, and extensible design. The async command execution pattern and Base64 encoding/decoding are the most complex parts but are essential for reliable operation.

The modular architecture makes it easy to add new features and commands while maintaining backward compatibility.
