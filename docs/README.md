# QEMU Guest Agent Wrapper

A Python-based command-line wrapper for communicating with QEMU Guest Agent (QGA) via Unix socket. This tool enables remote management of QEMU/KVM virtual machines from the host system.

## Features

- **Command Execution**: Execute arbitrary commands inside the guest VM
- **User Management**: Change user passwords remotely
- **System Information**: Query OS details, hostname, users, network interfaces, filesystems
- **SSH Key Management**: Add, remove, and list SSH authorized keys
- **File Operations**: Read and write files in the guest
- **Extensible Architecture**: Easy to add support for new QGA commands

## Requirements

- Python 3.8+
- QEMU with Guest Agent support
- Guest VM running `qemu-guest-agent`
- Unix socket for QGA communication (e.g., `/tmp/qga.sock`)

## Installation

1. Clone or download this repository:
```bash
cd qga-wrapper
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Connectivity Test

```bash
source venv/bin/activate
python qga_cli.py ping
```

### Get OS Information

```bash
python qga_cli.py osinfo
```

### Execute a Command

```bash
python qga_cli.py exec ls -la /home
```

### Get Network Interfaces

```bash
python qga_cli.py network
```

## CLI Usage

The `qga_cli.py` script provides a command-line interface to the wrapper:

```
usage: qga_cli.py [-h] [-s SOCKET] [-t TIMEOUT] [-j] {command} ...

Options:
  -s, --socket SOCKET   Path to QGA Unix socket (default: /tmp/qga.sock)
  -t, --timeout TIMEOUT Socket timeout in seconds (default: 30)
  -j, --json            Output in JSON format

Commands:
  ping                  Test connectivity to guest agent
  info                  Get guest agent information
  osinfo                Get operating system information
  hostname              Get guest hostname
  users                 Get logged-in users
  exec                  Execute command in guest
  set-password          Set user password
  network               Get network interface information
  fsinfo                Get filesystem information
  ssh-keys              Manage SSH authorized keys
  file-read             Read file from guest
  file-write            Write file to guest
```

### Command Examples

**Execute a command:**
```bash
python qga_cli.py exec whoami
python qga_cli.py exec ls -la /etc
python qga_cli.py exec cat /proc/cpuinfo
```

**Change a user password:**
```bash
python qga_cli.py set-password ubuntu newpassword123
```

**Get system information:**
```bash
python qga_cli.py osinfo
python qga_cli.py hostname
python qga_cli.py users
```

**Manage SSH keys:**
```bash
# List SSH keys
python qga_cli.py ssh-keys list ubuntu

# Add an SSH key
python qga_cli.py ssh-keys add ubuntu --key "ssh-rsa AAAAB3N..."

# Remove an SSH key
python qga_cli.py ssh-keys remove ubuntu --key "ssh-rsa AAAAB3N..."
```

**File operations:**
```bash
# Read a file
python qga_cli.py file-read /etc/hostname

# Write to a file
python qga_cli.py file-write /tmp/test.txt "Hello from host"
```

**JSON output:**
```bash
python qga_cli.py -j osinfo
python qga_cli.py -j network
```

## Python API Usage

You can also use the wrapper as a Python library:

```python
from qga_wrapper import QGAClient

# Using context manager (recommended)
with QGAClient('/tmp/qga.sock') as client:
    # Test connectivity
    if client.ping():
        print("Guest agent is responding")
    
    # Get OS information
    osinfo = client.get_osinfo()
    print(f"Running {osinfo['name']} {osinfo['version']}")
    
    # Execute a command
    result = client.run_command(['ls', '-la', '/home'])
    print(f"Output: {result['stdout']}")
    print(f"Exit code: {result['exitcode']}")
    
    # Change password
    client.set_user_password('ubuntu', 'newpassword')
    
    # Get network interfaces
    interfaces = client.get_network_interfaces()
    for iface in interfaces:
        print(f"Interface: {iface['name']}")
```

## Configuration

Edit `config.yaml` to customize settings:

```yaml
socket:
  path: /tmp/qga.sock
  timeout: 30

polling:
  interval: 0.1
  max_retries: 300

logging:
  level: INFO
```

## QEMU Setup

To use this wrapper, your QEMU VM must be configured with a QGA socket. Example QEMU command line:

```bash
qemu-system-aarch64 \
  -chardev socket,path=/tmp/qga.sock,server=on,wait=off,id=qga0 \
  -device virtio-serial \
  -device virtserialport,chardev=qga0,name=org.qemu.guest_agent.0 \
  # ... other QEMU options ...
```

Inside the guest VM, ensure `qemu-guest-agent` is installed and running:

```bash
# Ubuntu/Debian
sudo apt install qemu-guest-agent
sudo systemctl enable qemu-guest-agent
sudo systemctl start qemu-guest-agent

# Check status
sudo systemctl status qemu-guest-agent
```

## Supported QGA Commands

The wrapper currently supports:

### Information Gathering
- `guest-ping` - Test connectivity
- `guest-info` - Get agent information
- `guest-get-osinfo` - OS information
- `guest-get-host-name` - Hostname
- `guest-get-users` - Logged-in users
- `guest-get-timezone` - Timezone info
- `guest-network-get-interfaces` - Network interfaces
- `guest-get-fsinfo` - Filesystem information

### Command Execution
- `guest-exec` - Execute command (async)
- `guest-exec-status` - Get command status

### User Management
- `guest-set-user-password` - Change user password

### SSH Key Management
- `guest-ssh-get-authorized-keys` - List SSH keys
- `guest-ssh-add-authorized-keys` - Add SSH keys
- `guest-ssh-remove-authorized-keys` - Remove SSH keys

### File Operations
- `guest-file-open` - Open file
- `guest-file-close` - Close file
- `guest-file-read` - Read from file
- `guest-file-write` - Write to file

### Filesystem Management
- `guest-fsfreeze-freeze` - Freeze filesystems
- `guest-fsfreeze-thaw` - Thaw filesystems
- `guest-fsfreeze-status` - Get freeze status

### System Control
- `guest-shutdown` - Shutdown/reboot guest

## Extending the Wrapper

To add support for a new QGA command:

1. Add a method to the `QGAClient` class in `qga_wrapper.py`:

```python
def my_new_command(self, arg1, arg2):
    """Description of what this command does."""
    self._ensure_connected()
    arguments = {"param1": arg1, "param2": arg2}
    response = self._connection.send_command("guest-my-command", arguments)
    return response.get("return", {})
```

2. Optionally add a CLI command in `qga_cli.py`:

```python
def cmd_my_command(client, args):
    """Handle my-command CLI."""
    result = client.my_new_command(args.arg1, args.arg2)
    print(result)
    return 0
```

## Troubleshooting

### Connection Refused
- Ensure the QEMU VM is running
- Verify the socket path is correct
- Check that qemu-guest-agent is running in the guest
- Make sure no other process is holding the socket

### Timeout Errors
- Increase the timeout: `python qga_cli.py -t 60 <command>`
- Check if the guest agent is responsive: `python qga_cli.py ping`

### Permission Errors
- Ensure you have read/write access to the socket file
- Check file permissions: `ls -la /tmp/qga.sock`

## Architecture

The wrapper consists of three main components:

1. **QGAConnection**: Low-level socket communication and JSON-RPC handling
2. **QGAClient**: High-level API providing convenient methods for QGA operations
3. **CLI Interface**: Command-line tool built on top of QGAClient

See `DEVELOPMENT.md` for detailed implementation notes.

## License

This project is provided as-is for educational and development purposes.

## Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- New commands include docstrings
- CLI commands have help text
- Documentation is updated

## References

- [QEMU Guest Agent Protocol](https://wiki.qemu.org/Features/GuestAgent)
- [QGA JSON Protocol Specification](https://qemu.readthedocs.io/en/latest/interop/qemu-ga.html)
