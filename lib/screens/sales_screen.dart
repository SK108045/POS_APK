import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../state/pos_state.dart';
import '../models/order.dart';
import '../widgets/receipt_dialog.dart';

class SalesScreen extends StatefulWidget {
  final PosState posState;

  const SalesScreen({super.key, required this.posState});

  @override
  State<SalesScreen> createState() => _SalesScreenState();
}

class _SalesScreenState extends State<SalesScreen> {
  String _filter = 'all'; // all, cash, mpesa
  String _search = '';
  final TextEditingController _searchCtrl = TextEditingController();

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  List<Order> get _filteredOrders {
    var list = widget.posState.orders;
    if (_filter != 'all') {
      list = list.where((o) => o.paymentMethod.toLowerCase() == _filter).toList();
    }
    if (_search.isNotEmpty) {
      final s = _search.toLowerCase();
      list = list.where((o) =>
          o.ticketNo.toLowerCase().contains(s) ||
          o.customerName.toLowerCase().contains(s) ||
          o.paymentRef.toLowerCase().contains(s)).toList();
    }
    return list;
  }

  @override
  Widget build(BuildContext context) {
    final currencyFmt = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sales & Orders'),
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Search field
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                  hintText: 'Search by Ticket #, Ref or Customer...',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: _search.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear),
                          onPressed: () {
                            setState(() {
                              _searchCtrl.clear();
                              _search = '';
                            });
                          },
                        )
                      : null,
                  isDense: true,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onChanged: (v) => setState(() => _search = v.trim()),
              ),
            ),

            // Filter Chips
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Row(
                children: [
                  ChoiceChip(
                    label: const Text('All Orders'),
                    selected: _filter == 'all',
                    onSelected: (s) {
                      if (s) setState(() => _filter = 'all');
                    },
                  ),
                  const SizedBox(width: 8),
                  ChoiceChip(
                    label: const Text('💵 Cash'),
                    selected: _filter == 'cash',
                    onSelected: (s) {
                      if (s) setState(() => _filter = 'cash');
                    },
                  ),
                  const SizedBox(width: 8),
                  ChoiceChip(
                    label: const Text('📱 M-Pesa'),
                    selected: _filter == 'mpesa',
                    onSelected: (s) {
                      if (s) setState(() => _filter = 'mpesa');
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),

            // Orders list
            Expanded(
              child: _filteredOrders.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.receipt_long_outlined, size: 52, color: Colors.grey[400]),
                          const SizedBox(height: 8),
                          Text('No sales records found', style: TextStyle(color: Colors.grey[600])),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                      itemCount: _filteredOrders.length,
                      itemBuilder: (ctx, i) {
                        final order = _filteredOrders[i];
                        final dateStr = DateFormat('dd MMM yyyy, HH:mm')
                            .format(DateTime.fromMillisecondsSinceEpoch(order.createdAt * 1000));
                        final isMpesa = order.paymentMethod.toLowerCase() == 'mpesa';

                        return Card(
                          margin: const EdgeInsets.only(bottom: 10),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(12),
                            onTap: () {
                              showDialog(
                                context: context,
                                builder: (_) => ReceiptDialog(
                                  order: order,
                                  shopName: '${widget.posState.activeProfile.name} POS',
                                  shopTagline: widget.posState.activeProfile.tagline,
                                ),
                              );
                            },
                            child: Padding(
                              padding: const EdgeInsets.all(14),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        order.ticketNo,
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: isMpesa ? Colors.green.withOpacity(0.15) : Colors.blue.withOpacity(0.15),
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: Text(
                                          order.paymentMethod.toUpperCase(),
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.bold,
                                            color: isMpesa ? Colors.green[800] : Colors.blue[800],
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        '${order.items.length} item(s) • $dateStr',
                                        style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                                      ),
                                      Text(
                                        currencyFmt.format(order.total),
                                        style: TextStyle(
                                          fontSize: 15,
                                          fontWeight: FontWeight.w900,
                                          color: theme.colorScheme.primary,
                                        ),
                                      ),
                                    ],
                                  ),
                                  if (order.customerName.isNotEmpty) ...[
                                    const SizedBox(height: 4),
                                    Text(
                                      'Customer: ${order.customerName}',
                                      style: TextStyle(fontSize: 11, color: Colors.grey[700]),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
