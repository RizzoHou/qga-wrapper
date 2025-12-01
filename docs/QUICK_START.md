# QEMU Guest Agent Wrapper - Quick Start Guide

## Installation & Setup

```bash
python src/qga ping
```

### Get System Information

```bash
# OS info
python src/qga osinfo

# Hostname
python src/qga hostname

# Network interfaces
python src/qga network

# Filesystem info
python src/qga fsinfo
```

### Execute Commands

```bash
# Simple command
python src/qga exec whoami

# Command with arguments
python src/qga exec ls -la /home

# Show exit code
python src/qga exec -e cat /etc/hostname
```

### File Operations

```bash
# Read a file
python src/qga file-read /etc/hostname

# Write to a file
python src/qga file-write /tmp/test.txt "Hello World"
```

### JSON Output

```bash
# Get JSON output for any command
python src/qga -j osinfo
python src/qga -j network
```

## Python API Usage

```python
from qga_wrapper import QGAClient

# Basic usage
with QGAClient() as client:
    # Test connectivity
    if client.ping():
        print("Connected!")
    
    # Get OS info
    osinfo = client.get_osinfo()
    print(f"OS: {osinfo['name']} {osinfo['version']}")
    
    # Execute command
    result = client.run_command(['uname', '-a'])
    print(result['stdout'])
```

## Common Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `ping` | Test connectivity | `python src/qga ping` |
| `info` | Get agent info | `python src/qga info` |
| `osinfo` | OS information | `python src/qga osinfo` |
| `hostname` | Get hostname | `python src/qga hostname` |
| `users` | Logged-in users | `python src/qga users` |
| `exec` | Execute command | `python src/qga exec whoami` |
| `network` | Network info | `python src/qga network` |
| `fsinfo` | Filesystem info | `python src/qga fsinfo` |
| `file-read` | Read file | `python src/qga file-read /etc/hosts` |
| `file-write` | Write file | `python src/qga file-write /tmp/test.txt "data"` |

## Configuration

Default socket: `/tmp/qga.sock`

To use a different socket:
```bash
python src/qga -s /path/to/socket ping
```

To change timeout:
```bash
python src/qga -t 60 exec long_running_command
```

## Troubleshooting

**Connection Refused**:
- Ensure VM is running
- Check socket path: `ls -la /tmp/qga.sock`
- Verify qemu-guest-agent is running in guest

**Timeout Errors**:
- Increase timeout: `-t 60`
- Check guest agent status inside VM

**Permission Errors**:
- Check socket permissions
- Ensure you have access to the socket file

## Next Steps

- See `README.md` for comprehensive documentation
- See `DEVELOPMENT.md` for implementation details
- See `examples/example_usage.py` for more examples
