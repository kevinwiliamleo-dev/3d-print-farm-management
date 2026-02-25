import paramiko
import os

LOCAL_FILE = os.path.join(os.path.dirname(__file__), 'kit_api_new.py')
REMOTE_FILE = '/root/kit_api.py'
BACKUP_FILE = '/root/kit_api.py.bak'

print("Connecting to Orange Pi...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.4.197', port=22, username='root', password='Lumayanrahasia3',
            timeout=10, allow_agent=False, look_for_keys=False)
print("Connected!")

# Step 1: Backup existing
_, out, err = ssh.exec_command(f'cp {REMOTE_FILE} {BACKUP_FILE}')
out.read(); err.read()
print(f"Backup saved: {BACKUP_FILE}")

# Step 2: Upload new file via SFTP
sftp = ssh.open_sftp()
sftp.put(LOCAL_FILE, REMOTE_FILE)
sftp.close()
print(f"Uploaded new kit_api.py")

# Step 3: Verify file was written correctly
_, out, _ = ssh.exec_command('python3 -m py_compile /root/kit_api.py && echo "SYNTAX OK" || echo "SYNTAX ERROR"')
result = out.read().decode().strip()
print(f"Syntax check: {result}")

if "SYNTAX OK" not in result:
    # Rollback
    print("Rolling back...")
    _, out, _ = ssh.exec_command(f'cp {BACKUP_FILE} {REMOTE_FILE}')
    out.read()
else:
    # Step 4: Detect and restart the service
    _, out, _ = ssh.exec_command('systemctl list-units --all | grep -i kit')
    services = out.read().decode()
    print(f"\nDetected services:\n{services}")

    # Try both service names
    _, out, err = ssh.exec_command('systemctl restart kit.service; sleep 2; systemctl is-active kit.service')
    status = out.read().decode().strip()
    print(f"\nkit.service status: {status}")

    # Step 5: Test the new status endpoint
    import time
    time.sleep(2)
    _, out, _ = ssh.exec_command("curl -s 'http://localhost:5000/kit/fan?state=status'")
    status_resp = out.read().decode().strip()
    print(f"\nFan status endpoint test: {status_resp}")

    # Step 6: Show key diff
    _, out, _ = ssh.exec_command('grep -n "read_gpio_state\|gpio read\|current_fan_state" /root/kit_api.py')
    diff = out.read().decode()
    print(f"\nKey lines in new file:\n{diff}")

ssh.close()
print("\nDone!")
