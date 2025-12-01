#!/usr/bin/env python3
"""
QEMU Guest Agent CLI
====================
Command-line interface for the QEMU Guest Agent wrapper.

Usage:
    qga_cli.py ping
    qga_cli.py exec <command> [args...]
    qga_cli.py osinfo
    qga_cli.py hostname
    qga_cli.py users
    qga_cli.py set-password <username> <password>
    qga_cli.py network
    qga_cli.py fsinfo
"""

import sys
import argparse
import json
from qga_wrapper import QGAClient, QGAError, QGAConnectionError, QGAProtocolError


def format_output(data, output_format='text'):
    """Format output based on specified format."""
    if output_format == 'json':
        return json.dumps(data, indent=2)
    return str(data)


def cmd_ping(client, args):
    """Test connectivity to guest agent."""
    if client.ping():
        print("✓ Guest agent is responding")
        return 0
    else:
        print("✗ Guest agent is not responding")
        return 1


def cmd_info(client, args):
    """Get guest agent information."""
    info = client.get_info()
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"QGA Version: {info.get('version')}")
        print(f"\nSupported Commands ({len(info.get('supported_commands', []))}):")
        for cmd in info.get('supported_commands', []):
            status = "✓" if cmd.get('enabled') else "✗"
            print(f"  {status} {cmd.get('name')}")
    return 0


def cmd_osinfo(client, args):
    """Get operating system information."""
    osinfo = client.get_osinfo()
    if args.json:
        print(json.dumps(osinfo, indent=2))
    else:
        print(f"OS Name: {osinfo.get('name', 'N/A')}")
        print(f"Version: {osinfo.get('version', 'N/A')}")
        print(f"Kernel Version: {osinfo.get('kernel-version', 'N/A')}")
        print(f"Kernel Release: {osinfo.get('kernel-release', 'N/A')}")
        print(f"Machine: {osinfo.get('machine', 'N/A')}")
        print(f"ID: {osinfo.get('id', 'N/A')}")
    return 0


def cmd_hostname(client, args):
    """Get guest hostname."""
    hostname = client.get_hostname()
    print(hostname)
    return 0


def cmd_users(client, args):
    """Get logged-in users."""
    users = client.get_users()
    if args.json:
        print(json.dumps(users, indent=2))
    else:
        if not users:
            print("No users currently logged in")
        else:
            print(f"Logged-in Users ({len(users)}):")
            for user in users:
                print(f"  - {user.get('user', 'N/A')} (login time: {user.get('login-time', 'N/A')})")
    return 0


def cmd_exec(client, args):
    """Execute a command in the guest."""
    if not args.cmd:
        print("Error: No command specified", file=sys.stderr)
        return 1
    
    try:
        result = client.run_command(args.cmd)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result['stdout']:
                print(result['stdout'], end='')
            if result['stderr']:
                print(result['stderr'], file=sys.stderr, end='')
            if args.show_exitcode:
                print(f"\nExit code: {result['exitcode']}")
        
        return result['exitcode']
    except QGAError as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        return 1


def cmd_set_password(client, args):
    """Set user password."""
    try:
        client.set_user_password(args.username, args.password, crypted=args.crypted)
        print(f"✓ Password updated for user: {args.username}")
        return 0
    except QGAError as e:
        print(f"Error setting password: {e}", file=sys.stderr)
        return 1


def cmd_network(client, args):
    """Get network interface information."""
    interfaces = client.get_network_interfaces()
    if args.json:
        print(json.dumps(interfaces, indent=2))
    else:
        print(f"Network Interfaces ({len(interfaces)}):")
        for iface in interfaces:
            print(f"\n  {iface.get('name', 'N/A')}:")
            print(f"    Hardware Address: {iface.get('hardware-address', 'N/A')}")
            if 'ip-addresses' in iface:
                print(f"    IP Addresses:")
                for ip in iface.get('ip-addresses', []):
                    print(f"      - {ip.get('ip-address')} ({ip.get('ip-address-type')})")
    return 0


def cmd_fsinfo(client, args):
    """Get filesystem information."""
    fsinfo = client.get_fsinfo()
    if args.json:
        print(json.dumps(fsinfo, indent=2))
    else:
        print(f"Filesystems ({len(fsinfo)}):")
        for fs in fsinfo:
            print(f"\n  {fs.get('mountpoint', 'N/A')}:")
            print(f"    Type: {fs.get('type', 'N/A')}")
            print(f"    Disk: {', '.join([d.get('dev', 'N/A') for d in fs.get('disk', [])])}")
    return 0


def cmd_ssh_keys(client, args):
    """Manage SSH authorized keys."""
    if args.action == 'list':
        keys = client.ssh_get_authorized_keys(args.username)
        if args.json:
            print(json.dumps(keys, indent=2))
        else:
            print(f"SSH Keys for {args.username} ({len(keys)}):")
            for i, key in enumerate(keys, 1):
                print(f"{i}. {key[:60]}..." if len(key) > 60 else f"{i}. {key}")
        return 0
    
    elif args.action == 'add':
        if not args.key:
            print("Error: --key required for add action", file=sys.stderr)
            return 1
        client.ssh_add_authorized_keys(args.username, [args.key], reset=args.reset)
        print(f"✓ Added SSH key for user: {args.username}")
        return 0
    
    elif args.action == 'remove':
        if not args.key:
            print("Error: --key required for remove action", file=sys.stderr)
            return 1
        client.ssh_remove_authorized_keys(args.username, [args.key])
        print(f"✓ Removed SSH key for user: {args.username}")
        return 0


def cmd_file_read(client, args):
    """Read a file from the guest."""
    try:
        handle = client.file_open(args.path, 'r')
        content = client.file_read(handle)
        client.file_close(handle)
        print(content, end='')
        return 0
    except QGAError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1


def cmd_file_write(client, args):
    """Write content to a file in the guest."""
    try:
        handle = client.file_open(args.path, 'w')
        bytes_written = client.file_write(handle, args.content)
        client.file_close(handle)
        print(f"✓ Wrote {bytes_written} bytes to {args.path}")
        return 0
    except QGAError as e:
        print(f"Error writing file: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='QEMU Guest Agent CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-s', '--socket', default='/tmp/qga.sock',
                       help='Path to QGA Unix socket (default: /tmp/qga.sock)')
    parser.add_argument('-t', '--timeout', type=int, default=30,
                       help='Socket timeout in seconds (default: 30)')
    parser.add_argument('-j', '--json', action='store_true',
                       help='Output in JSON format')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Ping command
    subparsers.add_parser('ping', help='Test connectivity to guest agent')
    
    # Info command
    subparsers.add_parser('info', help='Get guest agent information')
    
    # OS Info command
    subparsers.add_parser('osinfo', help='Get operating system information')
    
    # Hostname command
    subparsers.add_parser('hostname', help='Get guest hostname')
    
    # Users command
    subparsers.add_parser('users', help='Get logged-in users')
    
    # Exec command
    exec_parser = subparsers.add_parser('exec', help='Execute command in guest')
    exec_parser.add_argument('-e', '--show-exitcode', action='store_true',
                            help='Show exit code')
    exec_parser.add_argument('cmd', nargs=argparse.REMAINDER, help='Command and arguments to execute')
    
    # Set password command
    pwd_parser = subparsers.add_parser('set-password', help='Set user password')
    pwd_parser.add_argument('username', help='Username')
    pwd_parser.add_argument('password', help='New password')
    pwd_parser.add_argument('--crypted', action='store_true',
                           help='Password is already crypted')
    
    # Network command
    subparsers.add_parser('network', help='Get network interface information')
    
    # Filesystem info command
    subparsers.add_parser('fsinfo', help='Get filesystem information')
    
    # SSH keys command
    ssh_parser = subparsers.add_parser('ssh-keys', help='Manage SSH authorized keys')
    ssh_parser.add_argument('action', choices=['list', 'add', 'remove'],
                           help='Action to perform')
    ssh_parser.add_argument('username', help='Username')
    ssh_parser.add_argument('--key', help='SSH public key (for add/remove)')
    ssh_parser.add_argument('--reset', action='store_true',
                           help='Reset all keys when adding (add only)')
    
    # File read command
    read_parser = subparsers.add_parser('file-read', help='Read file from guest')
    read_parser.add_argument('path', help='File path in guest')
    
    # File write command
    write_parser = subparsers.add_parser('file-write', help='Write file to guest')
    write_parser.add_argument('path', help='File path in guest')
    write_parser.add_argument('content', help='Content to write')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Map commands to handlers
    commands = {
        'ping': cmd_ping,
        'info': cmd_info,
        'osinfo': cmd_osinfo,
        'hostname': cmd_hostname,
        'users': cmd_users,
        'exec': cmd_exec,
        'set-password': cmd_set_password,
        'network': cmd_network,
        'fsinfo': cmd_fsinfo,
        'ssh-keys': cmd_ssh_keys,
        'file-read': cmd_file_read,
        'file-write': cmd_file_write,
    }
    
    try:
        with QGAClient(socket_path=args.socket, timeout=args.timeout) as client:
            handler = commands.get(args.command)
            if handler:
                return handler(client, args)
            else:
                print(f"Unknown command: {args.command}", file=sys.stderr)
                return 1
    
    except QGAConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        print("\nIs the QEMU VM running with QGA enabled?", file=sys.stderr)
        return 1
    except QGAProtocolError as e:
        print(f"Protocol error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
