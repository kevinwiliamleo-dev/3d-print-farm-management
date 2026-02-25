import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.4.197', port=22, username='root', password='Lumayanrahasia3',
            timeout=10, allow_agent=False, look_for_keys=False)

# Upload updated kit_api.py (setup_gpio no longer resets pin to 0)
sftp = ssh.open_sftp()
sftp.put('kit_api_new.py', '/root/kit_api.py')
sftp.close()
print("kit_api.py updated")

# Restart kit_api.service
_, out, _ = ssh.exec_command('systemctl restart kit_api.service; sleep 3; systemctl is-active kit_api.service')
print('Service status:', out.read().decode().strip())

# Turn fan ON
_, out, _ = ssh.exec_command('curl -s http://localhost:5000/kit/fan?state=on')
print('Fan ON:', out.read().decode().strip())

# Wait 10 seconds to verify kit_system doesn't reset it
print("Waiting 10s to verify fan stays ON...")
time.sleep(10)

_, out, _ = ssh.exec_command('gpio read 16')
gpio = out.read().decode().strip()
_, out, _ = ssh.exec_command('curl -s http://localhost:5000/kit/fan?state=status')
status = out.read().decode().strip()
print('GPIO after 10s:', gpio, '(expected: 1)')
print('Fan status after 10s:', status)

if gpio == '1':
    print("\n FAN STAYS ON - kita berhasil! kit_system tidak lagi reset GPIO")
else:
    print("\n Fan masih di-reset, perlu investigasi lebih lanjut")

# Turn fan OFF to clean state
_, out, _ = ssh.exec_command('curl -s http://localhost:5000/kit/fan?state=off')
print('\nFan OFF:', out.read().decode().strip())

ssh.close()
