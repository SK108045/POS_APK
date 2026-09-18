import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../state/pos_state.dart';

class ReportsScreen extends StatelessWidget {
  final PosState posState;

  const ReportsScreen({super.key, required this.posState});

  @override
  Widget build(BuildContext context) {
    final currencyFmt = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    final theme = Theme.of(context);
    final totalSales = posState.todaySales;
    final txnCount = posState.todayPaidCount;
    final avgOrder = txnCount > 0 ? (totalSales / txnCount) : 0.0;
    final breakdown = posState.salesByMethod;
    final cashAmount = breakdown['cash'] ?? 0.0;
    final mpesaAmount = breakdown['mpesa'] ?? 0.0;
    final totalSettled = cashAmount + mpesaAmount;

    final cashPercent = totalSettled > 0 ? (cashAmount / totalSettled) * 100 : 0.0;
    final mpesaPercent = totalSettled > 0 ? (mpesaAmount / totalSettled) * 100 : 0.0;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Reports & Analytics'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Store Header
              Row(
                children: [
                  Text(posState.activeProfile.icon, style: const TextStyle(fontSize: 26)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${posState.activeProfile.name} Daily Summary',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          DateFormat('EEEE, dd MMMM yyyy').format(DateTime.now()),
                          style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Overview Cards
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                color: theme.colorScheme.primaryContainer.withOpacity(0.6),
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      const Text('TOTAL GROSS SALES',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 0.8)),
                      const SizedBox(height: 6),
                      Text(
                        currencyFmt.format(totalSales),
                        style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.w900,
                          color: theme.colorScheme.primary,
                        ),
                      ),
                      const SizedBox(height: 14),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          Column(
                            children: [
                              Text('$txnCount',
                                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                              const Text('Transactions', style: TextStyle(fontSize: 11, color: Colors.grey)),
                            ],
                          ),
                          Container(width: 1, height: 24, color: Colors.grey[400]),
                          Column(
                            children: [
                              Text(currencyFmt.format(avgOrder),
                                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                              const Text('Avg Ticket', style: TextStyle(fontSize: 11, color: Colors.grey)),
                            ],
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Payment Methods Progress
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Settlement by Channel',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 14),

                      // Cash
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.money, size: 18, color: Colors.blue),
                              SizedBox(width: 6),
                              Text('Cash Register', style: TextStyle(fontWeight: FontWeight.w600)),
                            ],
                          ),
                          Text('${cashPercent.toStringAsFixed(1)}% (${currencyFmt.format(cashAmount)})',
                              style: const TextStyle(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 6),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: totalSettled > 0 ? (cashAmount / totalSettled) : 0,
                          backgroundColor: Colors.grey[200],
                          color: Colors.blue,
                          minHeight: 8,
                        ),
                      ),
                      const SizedBox(height: 16),

                      // M-Pesa
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.phone_android, size: 18, color: Colors.green),
                              SizedBox(width: 6),
                              Text('M-Pesa Till', style: TextStyle(fontWeight: FontWeight.w600)),
                            ],
                          ),
                          Text('${mpesaPercent.toStringAsFixed(1)}% (${currencyFmt.format(mpesaAmount)})',
                              style: const TextStyle(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 6),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: totalSettled > 0 ? (mpesaAmount / totalSettled) : 0,
                          backgroundColor: Colors.grey[200],
                          color: Colors.green,
                          minHeight: 8,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Hourly / Transaction Count info
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Store Activity Notes',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.check_circle_outline, color: Colors.green),
                        title: const Text('Catalog synchronization status'),
                        subtitle: Text('${posState.products.length} products loaded and ready for offline checkouts'),
                      ),
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.shield_outlined, color: Colors.blue),
                        title: const Text('Shift reconciliation'),
                        subtitle: const Text('All transactions signed and stored locally in encrypted device storage'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
