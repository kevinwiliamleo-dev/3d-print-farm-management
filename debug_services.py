import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.4.197', port=22, username='root', password='Lumayanrahasia3',
            timeout=10, allow_agent=False, look_for_keys=False)

# Check all kit-related services
_, out, _ = ssh.exec_command('systemctl list-units --all | grep -i kit')
print('=== All kit services ===')
print(out.read().decode())

# Check kit_system service definition
_, out, _ = ssh.exec_command('cat /etc/systemd/system/kit_system.service 2>/dev/null || echo "NOT FOUND"')
print('=== kit_system.service ===')
print(out.read().decode())

_, out, _ = ssh.exec_command('cat /etc/systemd/system/kit_api.service 2>/dev/null || echo "NOT FOUND"')
print('=== kit_api.service ===')
print(out.read().decode())

# Check what kit_system is doing
_, out, _ = ssh.exec_command('journalctl -u kit_system.service -n 10 --no-pager 2>/dev/null')
print('=== kit_system logs ===')
print(out.read().decode())

ssh.close()
