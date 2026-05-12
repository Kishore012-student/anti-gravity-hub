// Chart configuration
const ctx = document.getElementById('voltageChart').getContext('2d');
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = 'Inter';

const voltageChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [], // Time labels
        datasets: [{
            label: 'Battery Voltage (V)',
            data: [],
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHitRadius: 10
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                titleColor: '#f8fafc',
                bodyColor: '#f8fafc',
                borderColor: '#334155',
                borderWidth: 1
            }
        },
        scales: {
            x: {
                grid: {
                    color: '#334155',
                    drawBorder: false
                },
                ticks: {
                    maxTicksLimit: 10
                }
            },
            y: {
                min: 10,
                max: 15,
                grid: {
                    color: '#334155',
                    drawBorder: false
                }
            }
        },
        animation: {
            duration: 0 // Disable animation for smoother live updates
        }
    }
});

// Max data points on chart
const MAX_DATA_POINTS = 30;

// UI Elements
const els = {
    voltage: document.getElementById('valVoltage'),
    solar: document.getElementById('valSolar'),
    loadV: document.getElementById('valLoadV'),
    loadI: document.getElementById('valLoadI'),
    batteryPct: document.getElementById('valBatteryPct'),
    barVoltage: document.getElementById('barVoltage'),
    barBatteryPct: document.getElementById('barBatteryPct'),
    healthy: document.getElementById('valHealthy'),
    powerFlow: document.getElementById('powerFlowStatus'),
    relaySwitch: document.getElementById('relaySwitch'),
    ledSwitch: document.getElementById('ledSwitch'),
    btnEStop: document.getElementById('btnEStop'),
    alertContainer: document.getElementById('alertContainer'),
    modeBadge: document.getElementById('modeBadge'),
    connectionBadge: document.getElementById('connectionBadge'),
    networkUrl: document.getElementById('networkUrl'),
    systemLog: document.getElementById('systemLog'),
    statusToast: new bootstrap.Toast(document.getElementById('statusToast'))
};

function logEvent(message, type = 'info') {
    const div = document.createElement('div');
    const now = new Date().toLocaleTimeString();
    div.innerHTML = `<span class="text-muted">[${now}]</span> <span class="text-${type}">${message}</span>`;
    els.systemLog.prepend(div);
    // Keep only last 50 logs
    if (els.systemLog.children.length > 50) {
        els.systemLog.lastChild.remove();
    }
}

function showToast(message, color = 'bg-primary') {
    const toastEl = document.getElementById('statusToast');
    toastEl.className = `toast align-items-center text-white ${color} border-0`;
    toastEl.querySelector('.toast-body').textContent = message;
    els.statusToast.show();
}

// Generate QR Code when Modal Opens
document.getElementById('qrModal').addEventListener('shown.bs.modal', function () {
    const qrcodeContainer = document.getElementById("qrcode");
    qrcodeContainer.innerHTML = ""; // Clear old one
    
    new QRCode(qrcodeContainer, {
        text: window.location.origin,
        width: 250,
        height: 250,
        colorDark : "#000000",
        colorLight : "#ffffff",
        correctLevel : QRCode.CorrectLevel.H
    });
    
    els.networkUrl.textContent = window.location.origin;
});

// Control Flags to prevent infinite loops when updating switches
let isUpdatingUI = false;

// Fetch Data
async function fetchData() {
    try {
        const response = await fetch('/api/data');
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        
        updateUI(data);
        updateChart(data.voltage);
        
        // Update connection status
        els.connectionBadge.className = 'badge rounded-pill bg-success me-3 pulse-bg';
        els.connectionBadge.innerHTML = '<i class="fa-solid fa-wifi me-1"></i> Connected';
        
    } catch (error) {
        console.error('Error fetching data:', error);
        els.connectionBadge.className = 'badge rounded-pill bg-danger me-3';
        els.connectionBadge.innerHTML = '<i class="fa-solid fa-wifi-slash me-1"></i> Disconnected';
    }
}

// Update UI
function updateUI(data) {
    isUpdatingUI = true;

    // Mode Badge
    if (data.mock_mode) {
        els.modeBadge.className = 'badge rounded-pill bg-warning text-dark';
        els.modeBadge.innerHTML = '<i class="fa-solid fa-vial me-1"></i> Simulation Mode';
    } else {
        els.modeBadge.className = 'badge rounded-pill bg-primary';
        els.modeBadge.innerHTML = '<i class="fa-solid fa-microchip me-1"></i> Hardware Active';
    }

    // Numbers
    els.voltage.textContent = data.voltage.toFixed(1);
    els.solar.textContent = data.solar_voltage.toFixed(1);
    els.loadV.textContent = data.load_voltage.toFixed(1);
    els.loadI.textContent = data.load_current.toFixed(2);
    els.batteryPct.textContent = data.battery_pct;

    // Progress Bars
    els.barBatteryPct.style.width = `${data.battery_pct}%`;
    
    // Color code battery bar
    if (data.battery_pct > 50) {
        els.barBatteryPct.className = 'progress-bar bg-success';
    } else if (data.battery_pct > 20) {
        els.barBatteryPct.className = 'progress-bar bg-warning';
    } else {
        els.barBatteryPct.className = 'progress-bar bg-danger';
    }

    // Health Status
    if (data.system_healthy === 1 && data.emergency_stop === 0) {
        els.healthy.textContent = 'HEALTHY';
        els.healthy.className = 'fw-bold mb-0 text-success';
        els.alertContainer.style.display = 'none';
    } else if (data.emergency_stop === 1) {
        els.healthy.textContent = 'STOPPED';
        els.healthy.className = 'fw-bold mb-0 text-danger';
    } else {
        els.healthy.textContent = 'WARNING';
        els.healthy.className = 'fw-bold mb-0 text-warning';
        els.alertContainer.style.display = 'block';
    }

    // Power Flow
    if (data.power_flow === 1) {
        els.powerFlow.className = 'badge bg-success';
        els.powerFlow.innerHTML = '<i class="fa-solid fa-arrow-up"></i> Charging';
    } else if (data.power_flow === -1) {
        els.powerFlow.className = 'badge bg-warning text-dark';
        els.powerFlow.innerHTML = '<i class="fa-solid fa-arrow-down"></i> Discharging';
    } else {
        els.powerFlow.className = 'badge bg-secondary';
        els.powerFlow.innerHTML = '<i class="fa-solid fa-minus"></i> Idle';
    }

    // Switches (only update if user is not actively clicking them)
    els.relaySwitch.checked = data.relay === 1;
    els.ledSwitch.checked = data.led === 1;

    isUpdatingUI = false;
}

// Update Chart
function updateChart(voltage) {
    const now = new Date();
    const timeString = now.getHours().toString().padStart(2, '0') + ':' + 
                       now.getMinutes().toString().padStart(2, '0') + ':' + 
                       now.getSeconds().toString().padStart(2, '0');

    voltageChart.data.labels.push(timeString);
    voltageChart.data.datasets[0].data.push(voltage);

    if (voltageChart.data.labels.length > MAX_DATA_POINTS) {
        voltageChart.data.labels.shift();
        voltageChart.data.datasets[0].data.shift();
    }

    voltageChart.update();
}

// Send Command
async function sendCommand(command) {
    logEvent(`Sending command: ${command}...`, 'primary');
    try {
        const response = await fetch('/api/control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ command: command })
        });
        
        if (response.ok) {
            logEvent(`Hardware response: OK (${command})`, 'success');
            showToast(`Command ${command} confirmed.`, 'bg-success');
        }
        
        // Fetch immediately after sending to reflect changes faster
        fetchData();
    } catch (error) {
        logEvent(`Failed to send command: ${command}`, 'danger');
        showToast(`Command failed!`, 'bg-danger');
        console.error('Error sending command:', error);
    }
}

// Event Listeners
els.relaySwitch.addEventListener('change', (e) => {
    if (isUpdatingUI) return;
    sendCommand(e.target.checked ? 'RELAY_ON' : 'RELAY_OFF');
});

els.ledSwitch.addEventListener('change', (e) => {
    if (isUpdatingUI) return;
    sendCommand(e.target.checked ? 'LED_ON' : 'LED_OFF');
});

els.btnEStop.addEventListener('click', () => {
    sendCommand('ESTOP');
});

// Initial Fetch and Interval
fetchData();
setInterval(fetchData, 1000);
