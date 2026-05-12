import os
import threading
import time
import json
import socket
import random
from flask import Flask, render_template, jsonify, request

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

app = Flask(__name__)

# Check if running on Vercel
IS_VERCEL = "VERCEL" in os.environ

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

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def init_serial():
    global serial_port
    if serial is None: return False
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'Arduino' in port.description or 'CH340' in port.description or 'USB' in port.description:
            try:
                serial_port = serial.Serial(port.device, 9600, timeout=1)
                system_data["mock_mode"] = False
                return True
            except Exception as e:
                print(f"Failed to connect: {e}")
    return False

def background_task():
    global system_data, serial_port
    while True:
        if system_data["mock_mode"]:
            if not IS_VERCEL:
                init_serial()
            
            # Simulation Logic
            if system_data["emergency_stop"] == 0:
                system_data["solar_voltage"] = round(random.uniform(14.0, 18.5), 1)
                if system_data["relay"] == 1:
                    system_data["voltage"] = max(10.5, system_data["voltage"] - 0.02)
                    system_data["load_voltage"] = round(system_data["voltage"] - 0.2, 1)
                    system_data["load_current"] = round(random.uniform(0.5, 2.5), 2)
                    system_data["power_flow"] = -1
                else:
                    system_data["load_voltage"] = 0.0
                    system_data["load_current"] = 0.0
                    if system_data["solar_voltage"] > 14.0:
                        system_data["voltage"] = min(13.8, system_data["voltage"] + 0.02)
                        system_data["power_flow"] = 1
                    else:
                        system_data["power_flow"] = 0
                
                pct = ((system_data["voltage"] - 11.0) / (13.5 - 11.0)) * 100
                system_data["battery_pct"] = max(0, min(100, int(pct)))
                system_data["system_healthy"] = 1 if system_data["voltage"] > 11.5 else 0
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
            except Exception:
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

@app.route('/api/control', methods=['POST'])
def control():
    global system_data
    content = request.json
    command = content.get('command')
    
    if command == "RELAY_ON": system_data["relay"] = 1
    elif command == "RELAY_OFF": system_data["relay"] = 0
    elif command == "SYS_ON": system_data["emergency_stop"] = 0
    elif command == "ESTOP":
        system_data["emergency_stop"] = 1
        system_data["relay"] = 0
    elif command == "LED_ON": system_data["led"] = 1
    elif command == "LED_OFF": system_data["led"] = 0
        
    if not system_data["mock_mode"] and serial_port:
        try:
            with serial_lock:
                serial_port.write(f"{command}\n".encode('utf-8'))
        except Exception:
            pass
            
    return jsonify({"status": "success"})

if __name__ == '__main__':
    if not IS_VERCEL:
        init_serial()
        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()
        app.run(host='0.0.0.0', port=5000, debug=False)
