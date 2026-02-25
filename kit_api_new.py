from flask import Flask, request, jsonify
import subprocess
import threading
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
    # Baca nilai GPIO aktual dari hardware, bukan variabel memory
    # Sehingga akurat bahkan setelah service restart
    try:
        result = subprocess.check_output(f"gpio read {FAN_WPI_PIN}", shell=True)
        return result.strip() == b'1'
    except Exception:
        return False

def setup_gpio():
    # Only set pin direction (mode), do NOT reset value on startup.
    # This preserves fan state if service is restarted mid-operation.
    run_command(f"gpio mode {FAN_WPI_PIN} out")

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
        is_on = read_gpio_state()
        status_text = "ON" if is_on else "OFF"
        return jsonify({"status": status_text, "state": is_on})

    return jsonify({"error": "Invalid command"}), 400

@app.route('/kit/camera', methods=['GET'])
def camera_status():
    try:
        subprocess.check_output("netstat -tuln | grep 8081", shell=True)
        return jsonify({"status": "CAMERA RUNNING", "stream_url": "http://192.168.4.197:8081"})
    except Exception:
        return jsonify({"status": "CAMERA ERROR"}), 500

if __name__ == '__main__':
    setup_gpio()
    cam_thread = threading.Thread(target=run_ustreamer)
    cam_thread.start()
    print(" [INFO] Server Siap! Menunggu perintah...", file=sys.stderr)
    app.run(host='0.0.0.0', port=5000, debug=False)
