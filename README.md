# AetherControl: Anti-Gravity IoT Hub 🛰️

A professional IoT-based monitoring and control system for an Anti-Gravity hardware setup. Features a modern dark-mode dashboard, real-time telemetry, and mobile PWA integration.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FKishore012-student%2Fanti-gravity-hub)

## 🌟 Key Features
- **Real-Time Telemetry**: Monitor Battery Voltage, Solar Input, and Load Metrics.
- **Hardware Control**: Toggle Relay and LEDs directly from the dashboard.
- **Mobile Optimized**: Full PWA support with an installable mobile app and splash screen.
- **Cloud Showcase**: Hosted UI for remote demonstrations.

## 🛠️ Hardware Setup
- Arduino UNO
- Solar Panel & Battery Pack
- Relay Module & LED Array
- Voltage/Current Sensors

## 🚀 Quick Start
1. **Flash Arduino**: Upload `arduino_code/arduino_code.ino` to your Arduino UNO.
2. **Install Python Deps**: `pip install -r requirements.txt`
3. **Run Server**: `python app.py`
4. **Access Dashboard**: Open `http://localhost:5000` or scan the QR code for mobile access.

## 🏗️ Tech Stack
- **Backend**: Python Flask
- **Frontend**: Bootstrap 5, Chart.js, FontAwesome
- **Communication**: Pyserial (JSON Protocol)
- **Deployment**: Vercel & GitHub

Developed for Final Year Project.
