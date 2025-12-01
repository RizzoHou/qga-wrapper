# QEMU Guest Agent Wrapper

A professional Python wrapper for communicating with QEMU Guest Agent (QGA) via Unix socket, enabling remote management of QEMU/KVM virtual machines from the host system.

## 🚀 Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Test connectivity
python src/qga_cli.py ping

# Get system information
python src/qga_cli.py osinfo

# Execute a command
python src/qga_cli.py exec whoami
```

## 📁 Project Structure

```
qga-wrapper/
├── src/                      # Source code
│   ├── qga_wrapper.py       # Core wrapper library
│   └── qga_cli.py           # Command-line interface
├── docs/                     # Documentation
│   ├── README.md            # Comprehensive guide
│   ├── DEVELOPMENT.md       # Implementation details
│   └── QUICK_START.md       # Quick reference
├── config/                   # Configuration files
│   └── config.yaml          # Default configuration
├── examples/                 # Usage examples
│   └── example_usage.py     # Python API examples
├── data/                     # Data files
│   └── basic_info.json      # QGA capability info
├── venv/                     # Virtual environment
└── requirements.txt          # Python dependencies
```

## 📖 Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Get started in 5 minutes
- **[Full Documentation](docs/README.md)** - Comprehensive usage guide
- **[Development Notes](docs/DEVELOPMENT.md)** - Architecture & implementation details

## ✨ Features

- **Command Execution**: Run arbitrary commands in the guest VM
- **User Management**: Remote password changes
- **System Information**: Query OS, network, filesystem details
- **SSH Key Management**: Add, remove, list SSH authorized keys
- **File Operations**: Read and write files in the guest
- **Extensible Design**: Easy to add new QGA commands

## 🔧 Installation

1. Ensure you have Python 3.8+ installed
2. Virtual environment is already set up
3. Install dependencies:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## 💻 Usage Examples

### CLI Usage

```bash
# Test connectivity
python src/qga_cli.py ping

# Get OS information
python src/qga_cli.py osinfo

# Execute commands
python src/qga_cli.py exec ls -la /home

# Get network info
python src/qga_cli.py network

# Read a file from guest
python src/qga_cli.py file-read /etc/hostname

# JSON output
python src/qga_cli.py -j osinfo
```

### Python API Usage

```python
import sys
sys.path.insert(0, 'src')
from qga_wrapper import QGAClient

# Use context manager
with QGAClient() as client:
    # Test connectivity
    if client.ping():
        print("Connected!")
    
    # Get OS info
    osinfo = client.get_osinfo()
    print(f"OS: {osinfo['name']}")
    
    # Execute command
    result = client.run_command(['uname', '-a'])
    print(result['stdout'])
```

## 🎯 Supported Operations

### Information Gathering
- System info (OS, hostname, timezone)
- Network interfaces
- Filesystem information
- Logged-in users

### Command Execution
- Synchronous command execution
- Asynchronous command handling
- Output capture and decoding

### User & Access Management
- Password changes
- SSH key management

### File Operations
- Read files from guest
- Write files to guest

### System Control
- Shutdown/reboot guest

## ⚙️ Configuration

Default configuration is in `config/config.yaml`:

```yaml
socket:
  path: /tmp/qga.sock
  timeout: 30

polling:
  interval: 0.1
  max_retries: 300
```

## 🔍 QEMU Setup

Ensure your QEMU VM is configured with QGA:

```bash
qemu-system-aarch64 \
  -chardev socket,path=/tmp/qga.sock,server=on,wait=off,id=qga0 \
  -device virtio-serial \
  -device virtserialport,chardev=qga0,name=org.qemu.guest_agent.0 \
  # ... other options ...
```

Inside the guest:
```bash
# Install and start qemu-guest-agent
sudo apt install qemu-guest-agent
sudo systemctl enable --now qemu-guest-agent
```

## 🧪 Testing

Run the example script:
```bash
source venv/bin/activate
python examples/example_usage.py
```

## 🛠️ Troubleshooting

**Connection Refused:**
- Ensure VM is running
- Check socket path
- Verify qemu-guest-agent is running in guest

**Timeout Errors:**
- Increase timeout: `python src/qga_cli.py -t 60 <command>`
- Check guest agent status

**Permission Errors:**
- Check socket file permissions
- Ensure proper access rights

## 📦 Architecture

The wrapper uses a layered architecture:

1. **QGAConnection** (Low-level): Socket communication & JSON-RPC protocol
2. **QGAClient** (High-level): Convenient methods for QGA operations
3. **CLI Interface**: User-friendly command-line tool

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed architecture information.

## 🤝 Contributing

Contributions welcome! Please ensure:
- Code follows PEP 8 guidelines
- Methods include docstrings
- CLI commands have help text
- Documentation is updated

## 📄 License

This project is provided as-is for educational and development purposes.

## 📚 References

- [QEMU Guest Agent Protocol](https://wiki.qemu.org/Features/GuestAgent)
- [QGA JSON Protocol Specification](https://qemu.readthedocs.io/en/latest/interop/qemu-ga.html)

---

**Status**: ✅ Fully functional and tested with Ubuntu 24.04 LTS guest VM
