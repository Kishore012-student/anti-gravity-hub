import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';

void main() {
  runApp(const AetherControlApp());
}

class AetherControlApp extends StatelessWidget {
  const AetherControlApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AetherControl Mobile',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        primarySwatch: Colors.blue,
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        cardColor: const Color(0xFF1E293B),
        useMaterial3: true,
      ),
      home: const DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  // Configuration - Change this to your Vercel URL
  final String apiUrl = "https://aethercontrol-iot.vercel.app";
  
  Map<String, dynamic> data = {
    "voltage": 0.0,
    "solar_voltage": 0.0,
    "load_voltage": 0.0,
    "load_current": 0.0,
    "battery_pct": 0,
    "relay": 0,
    "led": 0,
    "system_healthy": 1,
    "power_flow": 0,
    "mock_mode": true
  };

  List<FlSpot> voltageHistory = [];
  List<dynamic> dataHistory = [];
  List<String> logs = ["[SYSTEM] AetherControl Mobile Initialized"];
  bool isConnected = false;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    fetchData();
    fetchHistory();
    timer = Timer.periodic(const Duration(seconds: 2), (t) {
      fetchData();
      if (t.tick % 30 == 0) fetchHistory(); // Fetch history every minute
    });
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  void addLog(String message, String type) {
    setState(() {
      final now = DateFormat('HH:mm:ss').format(DateTime.now());
      logs.insert(0, "[$now] $message");
      if (logs.length > 50) logs.removeLast();
    });
  }

  Future<void> fetchData() async {
    try {
      final response = await http.get(Uri.parse("$apiUrl/api/data")).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final newData = json.decode(response.body);
        setState(() {
          data = newData;
          isConnected = true;
          
          double v = (data['voltage'] as num).toDouble();
          voltageHistory.add(FlSpot(DateTime.now().millisecondsSinceEpoch.toDouble(), v));
          if (voltageHistory.length > 30) voltageHistory.removeAt(0);
        });
      }
    } catch (e) {
      setState(() {
        isConnected = false;
      });
    }
  }

  Future<void> fetchHistory() async {
    try {
      final response = await http.get(Uri.parse("$apiUrl/api/history")).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        setState(() {
          dataHistory = json.decode(response.body).reversed.toList();
        });
      }
    } catch (e) {
      print("History fetch error: $e");
    }
  }

  Future<void> sendCommand(String command) async {
    try {
      addLog("Sending: $command", "info");
      final response = await http.post(
        Uri.parse("$apiUrl/api/control"),
        headers: {"Content-Type": "application/json"},
        body: json.encode({"command": command}),
      );
      if (response.statusCode == 200) {
        addLog("Success: $command", "success");
        fetchData();
      }
    } catch (e) {
      addLog("Failed to send command", "error");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("AETHERCONTROL", style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2)),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: Icon(
              isConnected ? Icons.wifi : Icons.wifi_off,
              color: isConnected ? Colors.green : Colors.red,
            ),
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildModeBadge(),
            const SizedBox(height: 20),
            _buildMetricsGrid(),
            const SizedBox(height: 24),
            _buildChartCard(),
            const SizedBox(height: 24),
            _buildControlPanel(),
            const SizedBox(height: 24),
            _buildHistoryLog(),
            const SizedBox(height: 24),
            _buildEventLog(),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildModeBadge() {
    bool isMock = data['mock_mode'] ?? true;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: isMock ? Colors.orange.withOpacity(0.2) : Colors.blue.withOpacity(0.2),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: isMock ? Colors.orange : Colors.blue),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(isMock ? Icons.hourglass_empty : Icons.memory, size: 16, color: isMock ? Colors.orange : Colors.blue),
          const SizedBox(width: 8),
          Text(
            isMock ? "SEARCHING FOR HARDWARE..." : "HARDWARE ACTIVE",
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: isMock ? Colors.orange : Colors.blue),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricsGrid() {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 16,
      mainAxisSpacing: 16,
      childAspectRatio: 1.5,
      children: [
        _buildStatCard("Storage", "${data['voltage']}V", Icons.battery_charging_full, Colors.blue),
        _buildStatCard("Solar", "${data['solar_voltage']}V", Icons.solar_power, Colors.orange),
        _buildStatCard("Fuel Cell", "${data['load_voltage']}V", Icons.science, Colors.cyan),
        _buildStatCard("Total Gen", "${data['load_current']}V", Icons.bolt, Colors.redAccent),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey, fontWeight: FontWeight.bold)),
                Icon(icon, size: 18, color: color),
              ],
            ),
            Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  Widget _buildChartCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("Voltage Telemetry", style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 20),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: const FlGridData(show: false),
                  titlesData: const FlTitlesData(show: false),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [
                    LineChartBarData(
                      spots: voltageHistory,
                      isCurved: true,
                      color: Colors.blue,
                      barWidth: 3,
                      isStrokeCapRound: true,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(show: true, color: Colors.blue.withOpacity(0.1)),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlPanel() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("Control Panel", style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        Card(
          elevation: 0,
          child: Column(
            children: [
              SwitchListTile(
                title: const Text("Main Relay"),
                subtitle: const Text("Switch output power"),
                value: data['relay'] == 1,
                onChanged: (val) => sendCommand(val ? "RELAY_ON" : "RELAY_OFF"),
              ),
              const Divider(height: 1, indent: 16, endIndent: 16),
              SwitchListTile(
                title: const Text("Status LEDs"),
                subtitle: const Text("Toggle indicator lights"),
                value: data['led'] == 1,
                onChanged: (val) => sendCommand(val ? "LED_ON" : "LED_OFF"),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        ElevatedButton.icon(
          onPressed: () => sendCommand("ESTOP"),
          icon: const Icon(Icons.emergency),
          label: const Text("EMERGENCY STOP"),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.red,
            foregroundColor: Colors.white,
            minimumSize: const Size(double.infinity, 56),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        )
      ],
    );
  }

  Widget _buildHistoryLog() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text("Telemetry History", style: TextStyle(fontWeight: FontWeight.bold)),
            TextButton(onPressed: fetchHistory, child: const Text("Refresh", style: TextStyle(fontSize: 12))),
          ],
        ),
        const SizedBox(height: 8),
        Card(
          elevation: 0,
          child: SizedBox(
            height: 200,
            child: dataHistory.isEmpty 
              ? const Center(child: Text("No history data yet", style: TextStyle(color: Colors.grey)))
              : ListView.builder(
                padding: const EdgeInsets.all(8),
                itemCount: dataHistory.length,
                itemBuilder: (context, index) {
                  final item = dataHistory[index];
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4.0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(item['Timestamp'].toString().split(' ')[1], style: const TextStyle(fontSize: 12, color: Colors.blue)),
                        Text("${item['Battery_V']}V", style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        Text("${item['Load_V']}V / ${item['Load_A']}A", style: const TextStyle(fontSize: 11, color: Colors.grey)),
                      ],
                    ),
                  );
                },
              ),
          ),
        ),
      ],
    );
  }

  Widget _buildEventLog() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("System Event Log", style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        Container(
          height: 150,
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.black,
            borderRadius: BorderRadius.circular(12),
          ),
          child: ListView.builder(
            itemCount: logs.length,
            itemBuilder: (context, index) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 4.0),
                child: Text(
                  logs[index],
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: Colors.green),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
