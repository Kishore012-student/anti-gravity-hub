import os
import threading
import time
import json
import socket
import random
import csv
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file

# Check if running on Vercel
IS_VERCEL = "VERCEL" in os.environ

try:
    if not IS_VERCEL:
        import serial
        import serial.tools.list_ports
    else:
        serial = None
except ImportError:
    serial = None

app = Flask(__name__)

# Global state for the system
system_data = {
    "voltage": 12.0,
    "solar_voltage": 0.0,
    "load_voltage": 0.0,
    "load_current": 0.0,
    "battery_pct": 100,
    "relay": 0,
    "led": 0,
    "system_healthy": 1,
    "power_flow": 0,
    "emergency_stop": 0,
    "mock_mode": True 
}

serial_port = None
serial_lock = threading.Lock()
CSV_FILE = "aether_telemetry.csv"

def init_csv():
    try:
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Battery_V", "Solar_V", "Load_V", "Load_A", "Relay_State"])
    except:
        pass

def log_to_csv(data):
    if IS_VERCEL: return
    try:
        with open(CSV_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                data["voltage"],
                data["solar_voltage"],
                data["load_voltage"],
                data["load_current"],
                data["relay"]
            ])
    except:
        pass

def init_serial():
    global serial_port
    if serial is None: return False
    try:
        ports = serial.tools.list_ports.comports()
        if not ports: return False
        
        # 1. Try to find by name first
        for port in ports:
            if any(keyword in port.description for keyword in ['Arduino', 'CH340', 'USB', 'Serial']):
                serial_port = serial.Serial(port.device, 9600, timeout=1)
                system_data["mock_mode"] = False
                return True
        
        # 2. Fallback: Just try the first available port
        serial_port = serial.Serial(ports[0].device, 9600, timeout=1)
        system_data["mock_mode"] = False
        return True
    except:
        pass
    return False

def background_task():
    global system_data, serial_port
    while True:
        if system_data["mock_mode"]:
            if not IS_VERCEL:
                init_serial()
            time.sleep(1)
        else:
            try:
                if serial_port and serial_port.in_waiting > 0:
                    with serial_lock:
                        line = serial_port.readline().decode('utf-8').strip()
                    if line.startswith('{') and line.endswith('}'):
                        data = json.loads(line)
                        for key in data:
                            if key in system_data:
                                system_data[key] = data[key]
                        
                        if not IS_VERCEL and int(time.time()) % 60 == 0:
                            log_to_csv(system_data)
            except:
                system_data["mock_mode"] = True
            time.sleep(0.1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sw.js')
def sw():
    return app.send_static_file('js/sw.js')

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/logo.png')
def logo():
    return app.send_static_file('img/logo.png')

@app.route('/api/data')
def get_data():
    return jsonify(system_data)

@app.route('/api/history')
def get_history():
    history = []
    try:
        if not IS_VERCEL and os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode='r') as f:
                reader = csv.DictReader(f)
                history = list(reader)[-20:]
    except:
        pass
    return jsonify(history)

@app.route('/download/logs')
def download_logs():
    if not IS_VERCEL and os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "Logs only available when running on local hardware.", 403

@app.route('/api/control', methods=['POST'])
def control():
    global system_data
    content = request.json
    command = content.get('command')
    
    if command == "RELAY_ON": system_data["relay"] = 1
    elif command == "RELAY_OFF": system_data["relay"] = 0
    elif command == "ESTOP":
        system_data["emergency_stop"] = 1
        system_data["relay"] = 0
    elif command == "LED_ON": system_data["led"] = 1
    elif command == "LED_OFF": system_data["led"] = 0
        
    if not system_data["mock_mode"] and serial_port:
        try:
            with serial_lock:
                serial_port.write(f"{command}\n".encode('utf-8'))
        except:
            pass
            
    return jsonify({"status": "success"})

if __name__ == '__main__':
    if not IS_VERCEL:
        init_csv()
        init_serial()
        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()
        app.run(host='0.0.0.0', port=5000, debug=False)
