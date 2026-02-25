import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.4.197', port=22, username='root', password='Lumayanrahasia3', timeout=10, allow_agent=False, look_for_keys=False)

new_kit_api = r"""from flask import Flask, request, jsonify
import subprocess
import threading
import time
import sys

app = Flask(__name__)

# --- CORS HEADER ---
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

# --- KONFIGURASI ---
FAN_WPI_PIN = "16"
USTREAMER_CMD = "/root/ustreamer/ustreamer --device=/dev/video2 --format=mjpeg --resolution=1280x720 --io-method=mmap --desired-fps=30 --ignore-input-errors --host=0.0.0.0 --port=8081 --allow-origin=*"

def run_command(cmd):
    subprocess.run(cmd, shell=True)

def read_gpio_state():
    """Read actual GPIO pin value from hardware (not memory variable)"""
    try:
        result = subprocess.check_output(f"gpio read {FAN_WPI_PIN}", shell=True)
        return result.strip() == b'1'
    except Exception:
        return False

def setup_gpio():
    run_command(f"gpio mode {FAN_WPI_PIN} out")
    run_command(f"gpio write {FAN_WPI_PIN} 0")

def run_ustreamer():
    subprocess.Popen(USTREAMER_CMD, shell=True)

@app.route('/kit/fan', methods=['GET'])
def fan_control():
    state = request.args.get('state')

    print(f" [DEBUG] Menerima Perintah: {state}", file=sys.stderr)

    if state == 'on':
        run_command(f"gpio write {FAN_WPI_PIN} 1")
        return jsonify({"status": "FAN ON", "code": 200})

    elif state == 'off':
        run_command(f"gpio write {FAN_WPI_PIN} 0")
        return jsonify({"status": "FAN OFF", "code": 200})

    elif state == 'status':
        # Baca langsung dari GPIO hardware, bukan variabel memory
        # Sehingga tetap akurat meski service restart
        is_on = read_gpio_state()
        status_text = "ON" if is_on else "OFF"
        return jsonify({"status": status_text, "state": is_on})

    return jsonify({"error": "Invalid command"}), 400

@app.route('/kit/camera', methods=['GET'])
def camera_status():
    try:
        subprocess.check_output("netstat -tuln | grep 8081", shell=True)
        return jsonify({"status": "CAMERA RUNNING", "stream_url": "http://192.168.4.197:8081"})
    except:
        return jsonify({"status": "CAMERA ERROR"}), 500

if __name__ == '__main__':
    setup_gpio()

    # Jalankan Kamera
    cam_thread = threading.Thread(target=run_ustreamer)
    cam_thread.start()

    # Jalankan Server
    print(" [INFO] Server Siap! Menunggu perintah...", file=sys.stderr)
    app.run(host='0.0.0.0', port=5000, debug=False)
"""

# Backup dulu
_, out, err = ssh.exec_command('cp /root/kit_api.py /root/kit_api.py.bak')
out.read(); err.read()
print("Backup done")

# Write new file
sftp = ssh.open_sftp()
with sftp.open('/root/kit_api.py', 'w') as f:
    f.write(new_kit_api)
sftp.close()
print("File written")

# Verify
_, out, _ = ssh.exec_command('cat /root/kit_api.py')
print("=== New kit_api.py ===")
print(out.read().decode())

# Restart service
_, out, err = ssh.exec_command('systemctl restart kit.service 2>/dev/null || systemctl restart kit-api.service 2>/dev/null; sleep 2; systemctl status kit.service 2>/dev/null || systemctl status kit-api.service 2>/dev/null | head -20')
print("\n=== Service restart ===")
print(out.read().decode())
print(err.read().decode())

ssh.close()
