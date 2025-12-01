# QEMU Guest Agent Wrapper - Quick Start Guide

## Installation & Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Verify installation
pip list | grep PyYAML
```

## Basic Usage

### Test Connectivity
```bash
python qga_cli.py ping
```

### Get System Information
```bash
# OS info
python qga_cli.py osinfo

# Hostname
python qga_cli.py hostname

# Network interfaces
python qga_cli.py network

# Filesystem info
python qga_cli.py fsinfo
```

### Execute Commands
```bash
# Simple command
python qga_cli.py exec whoami

# Command with arguments
python qga_cli.py exec ls -la /home

# Show exit code
python qga_cli.py exec -e cat /etc/hostname
```

### File Operations
```bash
# Read a file
python qga_cli.py file-read /etc/hostname

# Write to a file
python qga_cli.py file-write /tmp/test.txt "Hello World"
```

### JSON Output
```bash
# Get JSON output for any command
python qga_cli.py -j osinfo
python qga_cli.py -j network
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
| `ping` | Test connectivity | `python qga_cli.py ping` |
| `info` | Get agent info | `python qga_cli.py info` |
| `osinfo` | OS information | `python qga_cli.py osinfo` |
| `hostname` | Get hostname | `python qga_cli.py hostname` |
| `users` | Logged-in users | `python qga_cli.py users` |
| `exec` | Execute command | `python qga_cli.py exec whoami` |
| `network` | Network info | `python qga_cli.py network` |
| `fsinfo` | Filesystem info | `python qga_cli.py fsinfo` |
| `file-read` | Read file | `python qga_cli.py file-read /etc/hosts` |
| `file-write` | Write file | `python qga_cli.py file-write /tmp/test.txt "data"` |

## Configuration

Default socket: `/tmp/qga.sock`

To use a different socket:
```bash
python qga_cli.py -s /path/to/socket ping
```

To change timeout:
```bash
python qga_cli.py -t 60 exec long_running_command
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
