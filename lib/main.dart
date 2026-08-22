import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const SydneyAIMaster());
}

// ============================================================
// APP
// ============================================================

class SydneyAIMaster extends StatefulWidget {
  const SydneyAIMaster({super.key});

  @override
  State<SydneyAIMaster> createState() => _SydneyAIMasterState();
}

class _SydneyAIMasterState extends State<SydneyAIMaster> {
  String bridgeIp = 'https://sydney-ea-api-1.onrender.com';

  void updateBridgeIp(String ip) {
    setState(() {
      bridgeIp = ip.trim();
    });
  }

  @override
  Widget build(BuildContext context) {
    final bridge = MT5BridgeService(bridgeIp);

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Sydney AI Master',
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0B1020),
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: MainNavigation(
        bridge: bridge,
        bridgeIp: bridgeIp,
        onBridgeIpChanged: updateBridgeIp,
      ),
    );
  }
}

// ============================================================
// BRIDGE SERVICE
// ============================================================

class MT5BridgeService {
  final String bridgeIp;

  MT5BridgeService(this.bridgeIp);

  String get baseUrl {
    final value = bridgeIp.trim();
    if (value.isEmpty) return 'https://sydney-ea-api-1.onrender.com';
    if (value.startsWith('http://') || value.startsWith('https://')) {
      return value.endsWith('/') ? value.substring(0, value.length - 1) : value;
    }
    return 'http://$value:8080';
  }

  Future<Map<String, dynamic>> getEndpoint(String endpoint) async {
    final response = await http
        .get(
          Uri.parse('$baseUrl$endpoint'),
        )
        .timeout(const Duration(seconds: 5));

    if (response.statusCode != 200) {
      throw Exception(
        'HTTP ${response.statusCode}: ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded is Map<String, dynamic>) {
      return decoded;
    }

    throw Exception('Invalid bridge response');
  }

  Future<Map<String, dynamic>> getStatus() {
    return getEndpoint('/api/status');
  }

  Future<Map<String, dynamic>> getAccount() {
    return getEndpoint('/api/account');
  }

  Future<Map<String, dynamic>> getAccountDetails() {
    return getEndpoint('/api/account');
  }

  Future<Map<String, dynamic>> getEA() {
    return getEndpoint('/api/ea');
  }

  Future<Map<String, dynamic>> getSignal() {
    return getEndpoint('/api/signal');
  }

  Future<Map<String, dynamic>> getTrades() {
    return getEndpoint('/api/trades');
  }

  Future<Map<String, dynamic>> scanMarket() {
    return getEndpoint('/api/scan');
  }
}

// ============================================================
// MAIN NAVIGATION
// ============================================================

class MainNavigation extends StatefulWidget {
  final MT5BridgeService bridge;
  final String bridgeIp;
  final ValueChanged<String> onBridgeIpChanged;

  const MainNavigation({
    super.key,
    required this.bridge,
    required this.bridgeIp,
    required this.onBridgeIpChanged,
  });

  @override
  State<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends State<MainNavigation> {
  int index = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      DashboardPage(bridge: widget.bridge),
      MyEAsPage(bridge: widget.bridge),
      AIScannerPage(bridge: widget.bridge),
      MT5Page(bridge: widget.bridge),
      SettingsPage(
        bridgeIp: widget.bridgeIp,
        onBridgeIpChanged: widget.onBridgeIpChanged,
        bridge: widget.bridge,
      ),
    ];

    return Scaffold(
      body: pages[index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (value) {
          setState(() {
            index = value;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.smart_toy_outlined),
            selectedIcon: Icon(Icons.smart_toy),
            label: 'My EAs',
          ),
          NavigationDestination(
            icon: Icon(Icons.analytics_outlined),
            selectedIcon: Icon(Icons.analytics),
            label: 'AI Scanner',
          ),
          NavigationDestination(
            icon: Icon(Icons.account_balance_outlined),
            selectedIcon: Icon(Icons.account_balance),
            label: 'MT5',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

// ============================================================
// DASHBOARD
// ============================================================

class DashboardPage extends StatefulWidget {
  final MT5BridgeService bridge;

  const DashboardPage({
    super.key,
    required this.bridge,
  });

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Map<String, dynamic>? status;
  Map<String, dynamic>? account;
  Map<String, dynamic>? ea;
  Map<String, dynamic>? signal;

  bool loading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    loadData();
  }

  Future<void> loadData() async {
    setState(() {
      loading = true;
      error = null;
    });

    try {
      final results = await Future.wait([
        widget.bridge.getStatus(),
        widget.bridge.getAccount(),
        widget.bridge.getEA(),
        widget.bridge.getSignal(),
      ]);

      if (!mounted) return;

      setState(() {
        status = results[0];
        account = results[1];
        ea = results[2];
        signal = results[3];
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        error = 'Cannot connect to the Python bridge.\n\n'
            'Check that:\n'
            '• Python bridge is running\n'
            '• Phone and PC use the same Wi-Fi\n'
            '• Bridge IP is correct\n\n'
            'Bridge: ${widget.bridge.baseUrl}';
        loading = false;
      });
    }
  }

  double numberValue(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse('$value') ?? 0;
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (error != null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Sydney AI Master'),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  Icons.cloud_off,
                  size: 70,
                  color: Colors.redAccent,
                ),
                const SizedBox(height: 20),
                Text(
                  error!,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 25),
                FilledButton.icon(
                  onPressed: loadData,
                  icon: const Icon(Icons.refresh),
                  label: const Text('RECONNECT'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final connected = status?['connected'] == true;

    final balance = numberValue(account?['balance']);
    final equity = numberValue(account?['equity']);

    final eaName = ea?['name'] ?? 'GhostkillerPro';
    final eaRunning = ea?['running'] == true;

    final direction = signal?['direction'] ?? 'NO TRADE';
    final confidence = numberValue(signal?['confidence']);

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Sydney AI Master',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(
            onPressed: loadData,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Trading Dashboard',
            style: TextStyle(
              fontSize: 26,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 8),

          Row(
            children: [
              statusDot(connected),
              const SizedBox(width: 8),
              Text(
                connected
                    ? 'BRIDGE CONNECTED'
                    : 'BRIDGE OFFLINE',
                style: TextStyle(
                  color: connected
                      ? Colors.greenAccent
                      : Colors.redAccent,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),

          const SizedBox(height: 22),

          Row(
            children: [
              Expanded(
                child: infoCard(
                  'Balance',
                  'R${balance.toStringAsFixed(2)}',
                  Icons.account_balance_wallet,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: infoCard(
                  'Equity',
                  'R${equity.toStringAsFixed(2)}',
                  Icons.show_chart,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          infoCard(
            'MT5',
            account?['platform'] ?? 'MetaTrader 5',
            Icons.candlestick_chart,
          ),

          const SizedBox(height: 24),

          const Text(
            'EA Status',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 10),

          appCard(
            child: Column(
              children: [
                Row(
                  children: [
                    statusDot(eaRunning),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        '$eaName',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    Text(
                      eaRunning ? 'RUNNING' : 'STOPPED',
                      style: TextStyle(
                        color: eaRunning
                            ? Colors.greenAccent
                            : Colors.redAccent,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 12),

                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '${ea?['symbol'] ?? 'XAUUSD'} • '
                    '${ea?['timeframe'] ?? 'M5'} • '
                    '${ea?['lot_size'] ?? 0} LOT',
                    style: const TextStyle(
                      color: Colors.grey,
                    ),
                  ),
                ),

                const SizedBox(height: 18),

                const Text(
                  'READ-ONLY MODE',
                  style: TextStyle(
                    color: Colors.orangeAccent,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          const Text(
            'AI Scanner',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 10),

          appCard(
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        signal?['symbol'] ?? 'XAUUSD',
                        style: const TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    Text(
                      '$direction',
                      style: TextStyle(
                        color: direction == 'BUY'
                            ? Colors.greenAccent
                            : direction == 'SELL'
                                ? Colors.redAccent
                                : Colors.grey,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 15),

                Text(
                  '${confidence.toStringAsFixed(0)} / 105',
                  style: const TextStyle(
                    fontSize: 35,
                    fontWeight: FontWeight.bold,
                    color: Colors.greenAccent,
                  ),
                ),

                const Text(
                  'AI CONFIDENCE',
                  style: TextStyle(color: Colors.grey),
                ),

                const SizedBox(height: 15),

                LinearProgressIndicator(
                  value: (confidence / 105).clamp(0.0, 1.0),
                  minHeight: 8,
                  borderRadius: BorderRadius.circular(10),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          appCard(
            child: Row(
              children: [
                const Icon(
                  Icons.lock_outline,
                  color: Colors.orangeAccent,
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Text(
                    'READ-ONLY MODE\n'
                    'No real trades can be sent.',
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================
// MY EAs
// ============================================================

class MyEAsPage extends StatefulWidget {
  final MT5BridgeService bridge;

  const MyEAsPage({
    super.key,
    required this.bridge,
  });

  @override
  State<MyEAsPage> createState() => _MyEAsPageState();
}

class _MyEAsPageState extends State<MyEAsPage> {
  Map<String, dynamic>? ea;
  bool loading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    loadEA();
  }

  Future<void> loadEA() async {
    try {
      final result = await widget.bridge.getEA();

      if (!mounted) return;

      setState(() {
        ea = result;
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        error = '$e';
        loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final running = ea?['running'] == true;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'My EAs',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(
            onPressed: loadEA,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: loading
          ? const Center(
              child: CircularProgressIndicator(),
            )
          : error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Text(
                      'Cannot load EA data.\n\n$error',
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    const Text(
                      'Expert Advisors',
                      style: TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 20),

                    appCard(
                      child: Column(
                        children: [
                          Row(
                            children: [
                              const Icon(
                                Icons.smart_toy,
                                size: 40,
                                color: Colors.blueAccent,
                              ),
                              const SizedBox(width: 15),
                              Expanded(
                                child: Text(
                                  ea?['name'] ??
                                      'GhostkillerPro',
                                  style: const TextStyle(
                                    fontSize: 20,
                                    fontWeight:
                                        FontWeight.bold,
                                  ),
                                ),
                              ),
                              statusDot(running),
                            ],
                          ),

                          const SizedBox(height: 20),

                          settingRow(
                            'Symbol',
                            '${ea?['symbol'] ?? 'XAUUSD'}',
                          ),

                          settingRow(
                            'Timeframe',
                            '${ea?['timeframe'] ?? 'M5'}',
                          ),

                          settingRow(
                            'Lot Size',
                            '${ea?['lot_size'] ?? 0}',
                          ),

                          settingRow(
                            'Open Trades',
                            '${ea?['open_trades'] ?? 0}',
                          ),

                          const SizedBox(height: 15),

                          const Text(
                            'READ-ONLY',
                            style: TextStyle(
                              color: Colors.orangeAccent,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
    );
  }
}

// ============================================================
// AI SCANNER
// ============================================================

class AIScannerPage extends StatefulWidget {
  final MT5BridgeService bridge;

  const AIScannerPage({
    super.key,
    required this.bridge,
  });

  @override
  State<AIScannerPage> createState() => _AIScannerPageState();
}

class _AIScannerPageState extends State<AIScannerPage> {
  Map<String, dynamic>? signal;
  bool loading = true;
  bool scanning = false;
  String? error;

  @override
  void initState() {
    super.initState();
    loadSignal();
  }

  Future<void> loadSignal() async {
    try {
      final result = await widget.bridge.getSignal();

      if (!mounted) return;

      setState(() {
        signal = result;
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        error = '$e';
        loading = false;
      });
    }
  }

  Future<void> scanMarket() async {
    setState(() {
      scanning = true;
      error = null;
    });
    try {
      final result = await widget.bridge.scanMarket();
      if (!mounted) return;
      setState(() {
        signal = result;
        scanning = false;
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        scanning = false;
        error = '$e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (error != null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('AI Scanner'),
        ),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.cloud_off,
                size: 60,
                color: Colors.redAccent,
              ),
              const SizedBox(height: 15),
              const Text('Cannot connect to bridge'),
              const SizedBox(height: 15),
              FilledButton(
                onPressed: loadSignal,
                child: const Text('RECONNECT'),
              ),
            ],
          ),
        ),
      );
    }

    final confidence =
        double.tryParse('${signal?['confidence'] ?? 0}') ?? 0;

    final direction =
        signal?['direction'] ?? 'NO TRADE';

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'AI Scanner',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(
            onPressed: loadSignal,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: scanning ? null : scanMarket,
              icon: scanning
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.radar),
              label: Text(scanning ? 'SCANNING MARKET...' : 'SCAN MARKET'),
            ),
          ),
          const SizedBox(height: 16),
          appCard(
            child: Column(
              children: [
                Text(
                  signal?['symbol'] ?? 'XAUUSD',
                  style: const TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),

                const SizedBox(height: 5),

                Text(
                  signal?['timeframe'] ?? 'M5',
                  style: const TextStyle(
                    color: Colors.grey,
                  ),
                ),

                const SizedBox(height: 25),

                Text(
                  '${confidence.toStringAsFixed(0)}',
                  style: const TextStyle(
                    fontSize: 55,
                    fontWeight: FontWeight.bold,
                    color: Colors.greenAccent,
                  ),
                ),

                const Text(
                  '/ 105 AI CONFIDENCE',
                  style: TextStyle(color: Colors.grey),
                ),

                const SizedBox(height: 15),

                Text(
                  direction == 'BUY'
                      ? 'BUY SIGNAL'
                      : direction == 'SELL'
                          ? 'SELL SIGNAL'
                          : 'NO TRADE',
                  style: TextStyle(
                    color: direction == 'BUY'
                        ? Colors.greenAccent
                        : direction == 'SELL'
                            ? Colors.redAccent
                            : Colors.grey,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),

                const SizedBox(height: 20),

                scannerRow(
                  'H1 Trend',
                  '${signal?['trend'] ?? 'Unknown'}',
                ),

                scannerRow(
                  'Liquidity Sweep',
                  signal?['liquidity_sweep'] == true
                      ? 'Confirmed'
                      : 'No',
                ),

                scannerRow(
                  'BOS',
                  signal?['bos'] == true
                      ? 'Confirmed'
                      : 'No',
                ),

                scannerRow(
                  'CHOCH',
                  signal?['choch'] == true
                      ? 'Confirmed'
                      : 'No',
                ),

                scannerRow(
                  'Order Block',
                  signal?['order_block'] == true
                      ? 'Fresh'
                      : 'None',
                ),

                scannerRow(
                  'FVG',
                  signal?['fvg'] == true
                      ? 'Present'
                      : 'None',
                ),

                scannerRow(
                  'Decision',
                  '${signal?['decision'] ?? 'NO TRADE'}',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================
// MT5 PAGE
// ============================================================

class MT5Page extends StatefulWidget {
  final MT5BridgeService bridge;

  const MT5Page({
    super.key,
    required this.bridge,
  });

  @override
  State<MT5Page> createState() => _MT5PageState();
}

class _MT5PageState extends State<MT5Page> {
  Map<String, dynamic>? status;
  Map<String, dynamic>? account;

  bool loading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    loadData();
  }

  Future<void> loadData() async {
    setState(() {
      loading = true;
      error = null;
    });

    try {
      final results = await Future.wait([
        widget.bridge.getStatus(),
        widget.bridge.getAccount(),
      ]);

      if (!mounted) return;

      setState(() {
        status = results[0];
        account = results[1];
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        error = '$e';
        loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final connected = status?['connected'] == true;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'MT5 Connection',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.transparent,
        actions: [
          IconButton(
            onPressed: loadData,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: loading
          ? const Center(
              child: CircularProgressIndicator(),
            )
          : error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      mainAxisAlignment:
                          MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.cloud_off,
                          size: 60,
                          color: Colors.redAccent,
                        ),
                        const SizedBox(height: 15),
                        const Text(
                          'Bridge unavailable',
                        ),
                        const SizedBox(height: 15),
                        FilledButton(
                          onPressed: loadData,
                          child: const Text('RECONNECT'),
                        ),
                      ],
                    ),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    appCard(
                      child: Column(
                        children: [
                          Icon(
                            connected
                                ? Icons.cloud_done
                                : Icons.cloud_off,
                            size: 65,
                            color: connected
                                ? Colors.greenAccent
                                : Colors.redAccent,
                          ),

                          const SizedBox(height: 12),

                          Text(
                            connected
                                ? 'BRIDGE CONNECTED'
                                : 'BRIDGE OFFLINE',
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              color: connected
                                  ? Colors.greenAccent
                                  : Colors.redAccent,
                            ),
                          ),

                          const SizedBox(height: 8),

                          Text(
                            '${status?['mt5'] ?? 'Unknown'}',
                            style: const TextStyle(
                              color: Colors.grey,
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 16),

                    appCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.account_balance, color: Colors.blueAccent, size: 30),
                              const SizedBox(width: 10),
                              const Expanded(
                                child: Text(
                                  'MT5 Account',
                                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                                ),
                              ),
                              statusDot(connected),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            connected ? 'MT5 TERMINAL CONNECTED' : 'MT5 TERMINAL OFFLINE',
                            style: TextStyle(
                              color: connected ? Colors.greenAccent : Colors.redAccent,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 15),
                          settingRow('Broker', '${account?['broker'] ?? '-'}'),
                          settingRow('Server', '${account?['server'] ?? '-'}'),
                          settingRow('Account', '${account?['login'] ?? account?['account'] ?? '-'}'),
                          settingRow('Currency', '${account?['currency'] ?? '-'}'),
                          settingRow('Platform', '${account?['platform'] ?? 'MetaTrader 5'}'),
                          settingRow('Symbol', '${account?['symbol'] ?? '-'}'),
                          settingRow('Timeframe', '${account?['timeframe'] ?? '-'}'),
                          settingRow('Balance', '${account?['balance'] ?? 0}'),
                          settingRow('Equity', '${account?['equity'] ?? 0}'),
                          settingRow('Free Margin', '${account?['free_margin'] ?? 0}'),
                          settingRow('Margin', '${account?['margin'] ?? 0}'),
                          settingRow('Leverage', '1:${account?['leverage'] ?? 0}'),
                        ],
                      ),
                    ),

                    const SizedBox(height: 18),

                    appCard(
                      child: Row(
                        children: [
                          const Icon(
                            Icons.lock,
                            color: Colors.orangeAccent,
                          ),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Text(
                              'Stage 3 is READ-ONLY.\n'
                              'No real trading commands are available.',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
    );
  }
}

// ============================================================
// SETTINGS
// ============================================================

class SettingsPage extends StatefulWidget {
  final String bridgeIp;
  final ValueChanged<String> onBridgeIpChanged;
  final MT5BridgeService bridge;

  const SettingsPage({
    super.key,
    required this.bridgeIp,
    required this.onBridgeIpChanged,
    required this.bridge,
  });

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late TextEditingController ipController;

  bool notifications = true;
  bool newsFilter = true;
  bool autoTrading = false;

  bool testing = false;
  String? testResult;

  @override
  void initState() {
    super.initState();

    ipController = TextEditingController(
      text: widget.bridgeIp,
    );
  }

  @override
  void dispose() {
    ipController.dispose();
    super.dispose();
  }

  Future<void> testConnection() async {
    final ip = ipController.text.trim();

    if (ip.isEmpty) {
      setState(() {
        testResult = 'Please enter the bridge URL.';
      });
      return;
    }

    widget.onBridgeIpChanged(ip);

    setState(() {
      testing = true;
      testResult = null;
    });

    try {
      final testBridge = MT5BridgeService(ip);
      final result = await testBridge.getEA();

      if (!mounted) return;

      setState(() {
        testing = false;
        testResult =
            'CONNECTED\n\n'
            'EA: ${result['name'] ?? 'Unknown'}\n'
            'Symbol: ${result['symbol'] ?? 'XAUUSD'}\n'
            'Timeframe: ${result['timeframe'] ?? 'M5'}';
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        testing = false;
        testResult =
            'CONNECTION FAILED\n\n'
            'Check the Render bridge URL and try again.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Settings',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.transparent,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Bridge Connection',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 8),

          const Text(
            'Enter the IP address of the PC running the '
            'Python MT5 Bridge.',
            style: TextStyle(color: Colors.grey),
          ),

          const SizedBox(height: 18),

          appCard(
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(
                      Icons.computer,
                      color: Colors.blueAccent,
                    ),
                    SizedBox(width: 10),
                    Text(
                      'Cloud Bridge URL',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 15),

                TextField(
                  controller: ipController,
                  keyboardType: TextInputType.url,
                  decoration: InputDecoration(
                    hintText: 'https://sydney-ea-api-1.onrender.com',
                    prefixIcon: const Icon(Icons.lan),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),

                const SizedBox(height: 15),

                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: testing
                        ? null
                        : testConnection,
                    icon: testing
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child:
                                CircularProgressIndicator(
                              strokeWidth: 2,
                            ),
                          )
                        : const Icon(Icons.wifi),
                    label: Text(
                      testing
                          ? 'TESTING...'
                          : 'TEST CONNECTION',
                    ),
                  ),
                ),

                if (testResult != null) ...[
                  const SizedBox(height: 18),

                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: testResult!
                              .startsWith('CONNECTED')
                          ? Colors.green.withOpacity(0.12)
                          : Colors.red.withOpacity(0.12),
                      borderRadius:
                          BorderRadius.circular(12),
                    ),
                    child: Text(
                      testResult!,
                      style: TextStyle(
                        color: testResult!
                                .startsWith('CONNECTED')
                            ? Colors.greenAccent
                            : Colors.redAccent,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),

          const SizedBox(height: 25),

          switchTile(
            'Notifications',
            'Trading alerts',
            Icons.notifications,
            notifications,
            (value) {
              setState(() {
                notifications = value;
              });
            },
          ),

          switchTile(
            'News Filter',
            'Avoid high-impact news',
            Icons.newspaper,
            newsFilter,
            (value) {
              setState(() {
                newsFilter = value;
              });
            },
          ),

          switchTile(
            'Auto Trading',
            'Disabled during Stage 3',
            Icons.auto_mode,
            autoTrading,
            (value) {
              setState(() {
                autoTrading = value;
              });
            },
          ),

          const SizedBox(height: 20),

          appCard(
            child: const Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Text(
                  'Sydney AI Master',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 10),
                Text(
                  'Stage 3',
                  style: TextStyle(
                    color: Colors.blueAccent,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 5),
                Text(
                  'Flutter → Python Bridge → MT5',
                  style: TextStyle(
                    color: Colors.grey,
                  ),
                ),
                SizedBox(height: 15),
                Text(
                  'READ-ONLY MODE',
                  style: TextStyle(
                    color: Colors.orangeAccent,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================
// UI HELPERS
// ============================================================

Widget appCard({
  required Widget child,
}) {
  return Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: const Color(0xFF151C30),
      borderRadius: BorderRadius.circular(16),
      border: Border.all(
        color: Colors.white10,
      ),
    ),
    child: child,
  );
}

Widget infoCard(
  String title,
  String value,
  IconData icon,
) {
  return appCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          color: Colors.blueAccent,
        ),
        const SizedBox(height: 10),
        Text(
          title,
          style: const TextStyle(
            color: Colors.grey,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 5),
        Text(
          value,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    ),
  );
}

Widget statusDot(bool active) {
  return Container(
    width: 12,
    height: 12,
    decoration: BoxDecoration(
      color: active
          ? Colors.greenAccent
          : Colors.redAccent,
      shape: BoxShape.circle,
    ),
  );
}

Widget settingRow(
  String title,
  String value,
) {
  return Padding(
    padding: const EdgeInsets.symmetric(
      vertical: 7,
    ),
    child: Row(
      mainAxisAlignment:
          MainAxisAlignment.spaceBetween,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: Colors.grey,
          ),
        ),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    ),
  );
}

Widget scannerRow(
  String title,
  String value,
) {
  return Padding(
    padding: const EdgeInsets.symmetric(
      vertical: 7,
    ),
    child: Row(
      children: [
        const Icon(
          Icons.check_circle,
          color: Colors.greenAccent,
          size: 19,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(title),
        ),
        Text(
          value,
          style: const TextStyle(
            color: Colors.greenAccent,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    ),
  );
}

Widget switchTile(
  String title,
  String subtitle,
  IconData icon,
  bool value,
  ValueChanged<bool> onChanged,
) {
  return Card(
    color: const Color(0xFF151C30),
    margin: const EdgeInsets.only(bottom: 10),
    child: SwitchListTile(
      secondary: Icon(
        icon,
        color: Colors.blueAccent,
      ),
      title: Text(
        title,
        style: const TextStyle(
          fontWeight: FontWeight.bold,
        ),
      ),
      subtitle: Text(subtitle),
      value: value,
      onChanged: onChanged,
    ),
  );
}