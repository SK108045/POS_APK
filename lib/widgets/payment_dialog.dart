import 'dart:math';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class PaymentDialog extends StatefulWidget {
  final double totalAmount;
  final Function(String method, String ref, String customer) onPay;

  const PaymentDialog({
    super.key,
    required this.totalAmount,
    required this.onPay,
  });

  @override
  State<PaymentDialog> createState() => _PaymentDialogState();
}

class _PaymentDialogState extends State<PaymentDialog> {
  String _method = 'cash';
  final TextEditingController _refCtrl = TextEditingController();
  final TextEditingController _customerCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _generateDefaultRef();
  }

  void _generateDefaultRef() {
    final rand = Random().nextInt(900000) + 100000;
    _refCtrl.text = _method == 'cash' ? 'CSH-$rand' : 'QA$rand';
  }

  @override
  void dispose() {
    _refCtrl.dispose();
    _customerCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final currencyFmt = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    final theme = Theme.of(context);

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 400),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Complete Payment',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Total Banner
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primaryContainer.withOpacity(0.5),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: theme.colorScheme.primary.withOpacity(0.3)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Amount Due:', style: TextStyle(fontWeight: FontWeight.w600)),
                    Text(
                      currencyFmt.format(widget.totalAmount),
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              // Method Selector
              const Text('Select Payment Mode', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: ChoiceChip(
                      label: const Center(
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.money, size: 18),
                            SizedBox(width: 6),
                            Text('Cash', style: TextStyle(fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                      selected: _method == 'cash',
                      onSelected: (val) {
                        if (val) {
                          setState(() {
                            _method = 'cash';
                            _generateDefaultRef();
                          });
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: ChoiceChip(
                      label: const Center(
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.phone_android, size: 18),
                            SizedBox(width: 6),
                            Text('M-Pesa', style: TextStyle(fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                      selected: _method == 'mpesa',
                      onSelected: (val) {
                        if (val) {
                          setState(() {
                            _method = 'mpesa';
                            _generateDefaultRef();
                          });
                        }
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              // Reference input
              TextField(
                controller: _refCtrl,
                decoration: InputDecoration(
                  labelText: _method == 'cash' ? 'Cash Receipt Ref' : 'M-Pesa Confirmation Code',
                  border: const OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 10),
              // Customer Name input (Optional)
              TextField(
                controller: _customerCtrl,
                decoration: const InputDecoration(
                  labelText: 'Customer Name (Optional)',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 20),
              FilledButton(
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  backgroundColor: _method == 'mpesa' ? Colors.green[700] : theme.colorScheme.primary,
                ),
                onPressed: () {
                  final ref = _refCtrl.text.trim().isEmpty ? 'TXN-DIRECT' : _refCtrl.text.trim();
                  widget.onPay(_method, ref, _customerCtrl.text.trim());
                  Navigator.pop(context);
                },
                child: Text(
                  'Confirm ${_method.toUpperCase()} Payment',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
