import paramiko, sys

host = '192.168.4.197'
user = 'root'
passwords = ['Lumayanrahasia3']

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for p in passwords:
    try:
        ssh.connect(host, port=22, username=user, password=p, timeout=5, allow_agent=False, look_for_keys=False)
        print(f'SUCCESS with password: {p}')

        cmds = [
            'uname -a',
            'ps aux | grep -E "python|node|fan|kit|flask" | grep -v grep',
            'ls -la /root/ /home/',
            'cat /etc/systemd/system/kit*.service 2>/dev/null || echo "no systemd service found"',
            'find / -maxdepth 5 -name "*.py" 2>/dev/null | grep -v __pycache__ | head -20',
        ]

        for cmd in cmds:
            print(f'\n=== {cmd} ===')
            _, out, err = ssh.exec_command(cmd)
            print(out.read().decode())
            e = err.read().decode()
            if e: print('STDERR:', e)

        ssh.close()
        sys.exit(0)
    except paramiko.AuthenticationException:
        print(f'Wrong: {p}')
    except Exception as e:
        print(f'Error ({p}): {e}')
        break

print('All passwords failed')
