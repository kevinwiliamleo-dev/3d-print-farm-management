import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.4.197', port=22, username='root', password='Lumayanrahasia3',
            timeout=10, allow_agent=False, look_for_keys=False)

# 1. Check GPIO pin 16 actual value
_, out, _ = ssh.exec_command('echo "GPIO read 16:"; gpio read 16')
print(out.read().decode())

# 2. Check kit_api service
_, out, _ = ssh.exec_command('systemctl is-active kit_api.service')
print('kit_api.service:', out.read().decode().strip())

# 3. Fan status via API
_, out, _ = ssh.exec_command('curl -s http://localhost:5000/kit/fan?state=status')
print('Fan status API:', out.read().decode().strip())

# 4. Try to turn fan ON manually via API, then read GPIO
_, out, _ = ssh.exec_command('curl -s http://localhost:5000/kit/fan?state=on')
print('Fan ON response:', out.read().decode().strip())

import time
time.sleep(1)
_, out, _ = ssh.exec_command('gpio read 16')
print('GPIO after ON command:', out.read().decode().strip())

# 5. Check all running kit processes
_, out, _ = ssh.exec_command('ps aux | grep kit_api | grep -v grep | head -5')
print('\nRunning processes:')
print(out.read().decode())

# 6. Check recent logs
_, out, _ = ssh.exec_command('journalctl -u kit_api.service -n 20 --no-pager 2>/dev/null | tail -20')
print('Recent kit_api logs:')
print(out.read().decode())

ssh.close()
