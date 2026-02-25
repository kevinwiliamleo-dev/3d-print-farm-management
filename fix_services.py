import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.4.197', port=22, username='root', password='Lumayanrahasia3',
            timeout=10, allow_agent=False, look_for_keys=False)

# Disable kit_system.service (duplicate of kit_api.service, keeps resetting GPIO)
_, out, err = ssh.exec_command('systemctl stop kit_system.service 2>&1; systemctl disable kit_system.service 2>&1')
print('=== Disable kit_system.service ===')
print(out.read().decode())
print(err.read().decode())

# Verify only one service running
_, out, _ = ssh.exec_command('systemctl list-units --all | grep kit')
print('=== Services after fix ===')
print(out.read().decode())

# Check fan state now (should stay ON without being reset)
import time
time.sleep(2)
_, out, _ = ssh.exec_command('curl -s http://localhost:5000/kit/fan?state=status')
print('Fan status:', out.read().decode().strip())

# GPIO read
_, out, _ = ssh.exec_command('gpio read 16')
print('GPIO 16:', out.read().decode().strip())

ssh.close()
print("Done!")
