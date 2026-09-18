import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../state/pos_state.dart';

class AdminScreen extends StatelessWidget {
  final PosState posState;

  const AdminScreen({super.key, required this.posState});

  @override
  Widget build(BuildContext context) {
    final currencyFmt = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    final theme = Theme.of(context);
    final profile = posState.activeProfile;
    final sales = posState.todaySales;
    final txnCount = posState.todayPaidCount;
    final methodBreakdown = posState.salesByMethod;
    final lowStockCount = posState.products.where((p) => p.stockQty <= 10).length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Portal'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: Icon(posState.isDarkMode ? Icons.light_mode : Icons.dark_mode),
            onPressed: () => posState.toggleTheme(),
            tooltip: 'Toggle Theme',
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header Card
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                color: theme.colorScheme.primaryContainer,
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 28,
                        backgroundColor: theme.colorScheme.primary,
                        child: Text(profile.icon, style: const TextStyle(fontSize: 28)),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${profile.name} Management',
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: theme.colorScheme.onPrimaryContainer,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Executive Dashboard & Store Control',
                              style: TextStyle(
                                fontSize: 13,
                                color: theme.colorScheme.onPrimaryContainer.withOpacity(0.8),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // KPI Metrics
              const Text('Performance Overview',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _buildKpiCard(
                      context,
                      title: 'Total Revenue',
                      value: currencyFmt.format(sales),
                      icon: Icons.payments,
                      color: Colors.green,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _buildKpiCard(
                      context,
                      title: 'Paid Orders',
                      value: '$txnCount txns',
                      icon: Icons.receipt_long,
                      color: Colors.blue,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _buildKpiCard(
                      context,
                      title: 'Products in Catalog',
                      value: '${posState.products.length} items',
                      icon: Icons.inventory_2,
                      color: Colors.purple,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _buildKpiCard(
                      context,
                      title: 'Low Stock Alert',
                      value: '$lowStockCount items',
                      icon: Icons.warning_amber,
                      color: lowStockCount > 0 ? Colors.orange : Colors.grey,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Payment Split
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Payment Settlement Split',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.blue.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: Colors.blue.withOpacity(0.3)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('💵 Cash Register',
                                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                  const SizedBox(height: 4),
                                  Text(
                                    currencyFmt.format(methodBreakdown['cash'] ?? 0),
                                    style: const TextStyle(
                                        fontSize: 16, fontWeight: FontWeight.w900, color: Colors.blue),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.green.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: Colors.green.withOpacity(0.3)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('📱 M-Pesa Till',
                                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                  const SizedBox(height: 4),
                                  Text(
                                    currencyFmt.format(methodBreakdown['mpesa'] ?? 0),
                                    style: const TextStyle(
                                        fontSize: 16, fontWeight: FontWeight.w900, color: Colors.green),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Staff Section
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Staff & Authorizations',
                              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                          Text('3 active users', style: TextStyle(fontSize: 12, color: Colors.grey)),
                        ],
                      ),
                      const SizedBox(height: 10),
                      _buildStaffTile('Admin Manager', 'PIN: 1234 (Master)', 'Full Access', Colors.indigo),
                      const Divider(height: 12),
                      _buildStaffTile('Lead Cashier', 'PIN: 5555', 'POS Terminal Only', Colors.teal),
                      const Divider(height: 12),
                      _buildStaffTile('Store Attendant', 'PIN: 7777', 'POS Terminal Only', Colors.brown),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Quick Actions
              FilledButton.icon(
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                icon: const Icon(Icons.point_of_sale),
                label: const Text('Return to POS Terminal', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                onPressed: () => Navigator.pop(context),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildKpiCard(
    BuildContext context, {
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title, style: const TextStyle(fontSize: 12, color: Colors.grey, fontWeight: FontWeight.w600)),
                Icon(icon, size: 18, color: color),
              ],
            ),
            const SizedBox(height: 8),
            Text(value, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: color)),
          ],
        ),
      ),
    );
  }

  Widget _buildStaffTile(String name, String pin, String role, Color badgeColor) {
    return Row(
      children: [
        CircleAvatar(
          radius: 16,
          backgroundColor: badgeColor.withOpacity(0.2),
          child: Text(name[0], style: TextStyle(color: badgeColor, fontWeight: FontWeight.bold, fontSize: 13)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              Text(pin, style: const TextStyle(fontSize: 11, color: Colors.grey)),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: badgeColor.withOpacity(0.12),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(role, style: TextStyle(fontSize: 11, color: badgeColor, fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }
}
