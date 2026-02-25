import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.4.67', port=22, username='root', password='Lumayanrahasia3',
            timeout=10, allow_agent=False, look_for_keys=False)

# Check container status
_, out, _ = ssh.exec_command("docker ps --format 'NAME={{.Names}} | STATUS={{.Status}} | CREATED={{.CreatedAt}}' 2>&1 | head -30")
print("=== Running Containers ===")
print(out.read().decode())

# Check recent image pulls
_, out, _ = ssh.exec_command("docker images --format 'REPO={{.Repository}} | TAG={{.Tag}} | CREATED={{.CreatedSince}}' 2>&1 | head -10")
print("=== Recent Images ===")
print(out.read().decode())

ssh.close()
