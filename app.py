import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request
import serial
import serial.tools.list_ports
import threading
import time
import json
import socket
import qrcode
import os
import random

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

def generate_qr_code(ip_address, port):
    url = f"http://{ip_address}:{port}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_dir = os.path.join(app.root_path, 'static', 'img')
    os.makedirs(img_dir, exist_ok=True)
    img_path = os.path.join(img_dir, 'qr.png')
    img.save(img_path)
    return img_path

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
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'Arduino' in port.description or 'CH340' in port.description or 'USB' in port.description:
            try:
                serial_port = serial.Serial(port.device, 9600, timeout=1)
                system_data["mock_mode"] = False
                print(f"Connected to Arduino on {port.device}")
                return True
            except Exception as e:
                print(f"Failed to connect to {port.device}: {e}")
    return False

def background_task():
    global system_data
    while True:
        if system_data["mock_mode"]:
            # Generate realistic mock data
            if system_data["emergency_stop"] == 0:
                system_data["solar_voltage"] = round(random.uniform(14.0, 18.5), 1)
                
                # Simulate battery drain or charge based on relay and solar
                if system_data["relay"] == 1:
                    system_data["voltage"] = max(10.5, system_data["voltage"] - random.uniform(0.01, 0.05))
                    system_data["load_voltage"] = round(system_data["voltage"] - 0.2, 1)
                    system_data["load_current"] = round(random.uniform(0.5, 2.5), 2)
                    system_data["power_flow"] = -1 # Discharging
                else:
                    system_data["load_voltage"] = 0.0
                    system_data["load_current"] = 0.0
                    if system_data["solar_voltage"] > 14.0:
                        system_data["voltage"] = min(13.8, system_data["voltage"] + random.uniform(0.01, 0.05))
                        system_data["power_flow"] = 1 # Charging
                    else:
                        system_data["power_flow"] = 0 # Idle
                
                # Calculate percentage (approximate lead-acid curve)
                pct = ((system_data["voltage"] - 11.0) / (13.5 - 11.0)) * 100
                system_data["battery_pct"] = max(0, min(100, int(pct)))
                
                # Health check
                if system_data["voltage"] < 11.5:
                    system_data["system_healthy"] = 0
                else:
                    system_data["system_healthy"] = 1
            time.sleep(1)
        else:
            # Read from real serial port
            try:
                if serial_port and serial_port.in_waiting > 0:
                    with serial_lock:
                        line = serial_port.readline().decode('utf-8').strip()
                    if line.startswith('{') and line.endswith('}'):
                        try:
                            data = json.loads(line)
                            for key in data:
                                if key in system_data:
                                    system_data[key] = data[key]
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                print(f"Serial read error: {e}")
                system_data["mock_mode"] = True # Fallback to mock mode if connection lost
            time.sleep(0.1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sw.js')
def sw():
    return app.send_static_file('../sw.js')

@app.route('/api/data')
def get_data():
    return jsonify(system_data)

@app.route('/api/control', methods=['POST'])
def control():
    global system_data
    content = request.json
    command = content.get('command')
    
    # Handle the command locally in state
    if command == "RELAY_ON":
        system_data["relay"] = 1
    elif command == "RELAY_OFF":
        system_data["relay"] = 0
    elif command == "SYS_ON":
        system_data["emergency_stop"] = 0
    elif command == "ESTOP":
        system_data["emergency_stop"] = 1
        system_data["relay"] = 0 # Force relay off
        system_data["power_flow"] = 0
    elif command == "LED_ON":
        system_data["led"] = 1
    elif command == "LED_OFF":
        system_data["led"] = 0
        
    # Send command to Arduino if connected
    if not system_data["mock_mode"] and serial_port:
        try:
            with serial_lock:
                # Send simple commands terminated by newline
                serial_port.write(f"{command}\n".encode('utf-8'))
        except Exception as e:
            print(f"Failed to send command to Arduino: {e}")
            
    return jsonify({"status": "success", "command": command})

if __name__ == '__main__':
    # Initialize hardware connection (Only if NOT on Vercel)
    if not IS_VERCEL:
        init_serial()
        
        # Start background data loop
        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()
        
        # Network setup
        port = 5000
        local_ip = get_local_ip()
        generate_qr_code(local_ip, port)
        
        print(f"*" * 50)
        print(f"* Anti-Gravity Hub Running!")
        print(f"* Local access: http://127.0.0.1:{port}")
        print(f"* Network access: http://{local_ip}:{port}")
        print(f"* QR code generated at static/img/qr.png")
        print(f"*" * 50)
        
        # Run the server on all interfaces so mobile can connect
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Vercel handles the run, but we need to ensure some state is initialized
        pass
else:
    # This block runs when imported by Vercel's serverless handler
    if not IS_VERCEL: # Fallback if env var isn't set but it is being imported
        pass
    # For Vercel, we can't run a background thread easily, 
    # so it will default to the initial system_data values.
    pass
