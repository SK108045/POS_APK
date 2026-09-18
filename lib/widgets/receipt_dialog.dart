import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/order.dart';

class ReceiptDialog extends StatelessWidget {
  final Order order;
  final String shopName;
  final String shopTagline;

  const ReceiptDialog({
    super.key,
    required this.order,
    required this.shopName,
    required this.shopTagline,
  });

  @override
  Widget build(BuildContext context) {
    final currencyFmt = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    final dateStr = DateFormat('dd MMM yyyy, HH:mm')
        .format(DateTime.fromMillisecondsSinceEpoch(order.createdAt * 1000));

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 380),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Center(
                child: Column(
                  children: [
                    const Icon(Icons.receipt_long, size: 44, color: Colors.green),
                    const SizedBox(height: 8),
                    Text(
                      shopName,
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                      textAlign: TextAlign.center,
                    ),
                    if (shopTagline.isNotEmpty)
                      Text(
                        shopTagline,
                        style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                        textAlign: TextAlign.center,
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              const Divider(),
              // Metadata
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Ticket: ${order.ticketNo}',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  Text(dateStr, style: TextStyle(fontSize: 12, color: Colors.grey[600])),
                ],
              ),
              if (order.customerName.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text('Customer: ${order.customerName}',
                      style: TextStyle(fontSize: 12, color: Colors.grey[700])),
                ),
              const Divider(),
              const SizedBox(height: 8),

              // Item lines
              ...order.items.map((it) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          '${it.qty}x ${it.name}',
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                        ),
                      ),
                      Text(
                        currencyFmt.format(it.lineTotal),
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                );
              }),

              const SizedBox(height: 12),
              const Divider(),
              // Totals
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('GRAND TOTAL',
                      style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  Text(
                    currencyFmt.format(order.total),
                    style: const TextStyle(
                        fontWeight: FontWeight.w900, fontSize: 18, color: Colors.green),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Payment Method: ${order.paymentMethod.toUpperCase()}',
                      style: TextStyle(fontSize: 12, color: Colors.grey[700])),
                  Text('Ref: ${order.paymentRef}',
                      style: TextStyle(fontSize: 12, color: Colors.grey[600], fontFamily: 'monospace')),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(),
              Center(
                child: Text(
                  'Thank you for your visit!\n------- END OF RECEIPT -------',
                  style: TextStyle(fontSize: 11, color: Colors.grey[500]),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 16),
              FilledButton(
                style: FilledButton.styleFrom(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
                onPressed: () => Navigator.pop(context),
                child: const Text('Close Receipt', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
