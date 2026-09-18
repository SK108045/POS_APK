import 'package:flutter/material.dart';

class PinPadWidget extends StatelessWidget {
  final ValueChanged<String> onKeyPress;
  final VoidCallback onClear;
  final VoidCallback onEnter;

  const PinPadWidget({
    super.key,
    required this.onKeyPress,
    required this.onClear,
    required this.onEnter,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildRow(context, ['1', '2', '3']),
        const SizedBox(height: 8),
        _buildRow(context, ['4', '5', '6']),
        const SizedBox(height: 8),
        _buildRow(context, ['7', '8', '9']),
        const SizedBox(height: 8),
        _buildBottomRow(context),
      ],
    );
  }

  Widget _buildRow(BuildContext context, List<String> keys) {
    return Row(
      children: keys.map((k) {
        return Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4.0),
            child: SizedBox(
              height: 52,
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  textStyle: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                onPressed: () => onKeyPress(k),
                child: Text(k),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildBottomRow(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4.0),
            child: SizedBox(
              height: 52,
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: onClear,
                child: const Text('Clear', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
              ),
            ),
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4.0),
            child: SizedBox(
              height: 52,
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  textStyle: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                onPressed: () => onKeyPress('0'),
                child: const Text('0'),
              ),
            ),
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4.0),
            child: SizedBox(
              height: 52,
              child: FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: theme.colorScheme.primary,
                  foregroundColor: theme.colorScheme.onPrimary,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: onEnter,
                child: const Text('Enter', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
