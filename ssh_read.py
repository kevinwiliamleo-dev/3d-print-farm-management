import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.4.197', port=22, username='root', password='Lumayanrahasia3', timeout=10, allow_agent=False, look_for_keys=False)

# Read kit_api.py
_, out, _ = ssh.exec_command('cat /root/kit_api.py')
print("=== /root/kit_api.py ===")
print(out.read().decode())

# Check GPIO/pin config
_, out, _ = ssh.exec_command('gpio readall 2>/dev/null || echo "gpio not available"')
print("\n=== GPIO State ===")
print(out.read().decode())

# Check what's listening on port 5000
_, out, _ = ssh.exec_command('ss -tlnp | grep 5000')
print("\n=== Port 5000 ===")
print(out.read().decode())

ssh.close()
