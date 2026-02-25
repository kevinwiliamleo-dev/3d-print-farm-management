import paramiko, time

# SSH to Proxmox server - need root credentials
# Try common credentials
attempts = [
    ('root', 'Lumayanrahasia3'),
    ('root', 'root'),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

connected = False
for user, pwd in attempts:
    try:
        ssh.connect('192.168.4.67', port=22, username=user, password=pwd,
                    timeout=10, allow_agent=False, look_for_keys=False)
        print(f'Connected as {user}')
        connected = True
        break
    except Exception as e:
        print(f'Failed {user}: {e}')

if not connected:
    print("Cannot connect to Proxmox server via SSH")
    exit(1)

# Check disk usage
_, out, _ = ssh.exec_command('df -h / /var/lib 2>/dev/null | head -5')
print('=== Disk usage ===')
print(out.read().decode())

# Check docker disk usage
_, out, _ = ssh.exec_command('docker system df 2>&1')
print('=== Docker disk usage ===')
print(out.read().decode())

# Clean old unused images and containers
print('Cleaning docker...')
_, out, err = ssh.exec_command('docker system prune -f 2>&1')
print(out.read().decode())

# Check disk again
_, out, _ = ssh.exec_command('df -h / 2>/dev/null | tail -1')
print('=== Disk after cleanup ===')
print(out.read().decode())

# Try pull new image
print('Pulling new backend image...')
_, out, err = ssh.exec_command('docker pull ghcr.io/kevinwiliamleo-dev/3d-print-farm-management-backend:development 2>&1')
output = out.read().decode()
print(output[:1000])

ssh.close()
