import 'package:flutter/material.dart';
import '../models/business_profile.dart';
import '../state/pos_state.dart';
import '../widgets/pin_pad_widget.dart';
import 'admin_screen.dart';

class LoginScreen extends StatefulWidget {
  final PosState posState;

  const LoginScreen({super.key, required this.posState});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  late String _selectedProfileId;
  String _pin = '';
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _selectedProfileId = widget.posState.activeProfile.id;
  }

  void _onKeyPress(String key) {
    if (_pin.length < 6) {
      setState(() {
        _pin += key;
        _errorMessage = null;
      });
    }
  }

  void _onClear() {
    setState(() {
      _pin = '';
      _errorMessage = null;
    });
  }

  Future<void> _submitLogin() async {
    final success = await widget.posState.login(_selectedProfileId, _pin.isEmpty ? '1234' : _pin);
    if (!success) {
      setState(() {
        _errorMessage = 'Invalid PIN. Try default: 1234';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final activeProfile = BusinessProfile.getById(_selectedProfileId);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Staff Access'),
        actions: [
          IconButton(
            icon: Icon(widget.posState.isDarkMode ? Icons.light_mode : Icons.dark_mode),
            tooltip: 'Toggle Theme',
            onPressed: () => widget.posState.toggleTheme(),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Card(
                elevation: 4,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                child: Padding(
                  padding: const EdgeInsets.all(22.0),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Brand Header
                      Row(
                        children: [
                          Container(
                            width: 52,
                            height: 52,
                            decoration: BoxDecoration(
                              color: theme.colorScheme.primary.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: theme.colorScheme.primary.withOpacity(0.3)),
                            ),
                            child: Center(
                              child: Text(activeProfile.icon, style: const TextStyle(fontSize: 28)),
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${activeProfile.name} POS',
                                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                                ),
                                Text(
                                  activeProfile.tagline,
                                  style: TextStyle(fontSize: 11, color: Colors.grey[600]),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 18),

                      // Store Category Selector (ONLY here before login)
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.surfaceVariant.withOpacity(0.3),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: theme.dividerColor),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Text(
                                    '🏢 SELECT STORE CATEGORY',
                                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                                  ),
                                ),
                                Text(
                                  'Choose before login',
                                  style: TextStyle(fontSize: 10, color: Colors.grey),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 6,
                              runSpacing: 6,
                              children: BusinessProfile.allProfiles.map((prof) {
                                final isSelected = prof.id == _selectedProfileId;
                                return ChoiceChip(
                                  label: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(prof.icon, style: const TextStyle(fontSize: 15)),
                                      const SizedBox(width: 6),
                                      Text(prof.name, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                                      if (isSelected) ...[
                                        const SizedBox(width: 4),
                                        const Icon(Icons.check, size: 14),
                                      ],
                                    ],
                                  ),
                                  selected: isSelected,
                                  onSelected: (selected) {
                                    if (selected) {
                                      setState(() {
                                        _selectedProfileId = prof.id;
                                      });
                                    }
                                  },
                                );
                              }).toList(),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),

                      // 1-Click Demo Login
                      FilledButton.icon(
                        style: FilledButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        icon: const Icon(Icons.bolt, size: 20),
                        label: const Text('1-Click Demo Login (PIN: 1234)',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                        onPressed: () {
                          _pin = '1234';
                          _submitLogin();
                        },
                      ),
                      const SizedBox(height: 12),

                      // Divider
                      Row(
                        children: [
                          const Expanded(child: Divider()),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 10),
                            child: Text('OR ENTER PIN', style: TextStyle(fontSize: 11, color: Colors.grey[600])),
                          ),
                          const Expanded(child: Divider()),
                        ],
                      ),
                      const SizedBox(height: 10),

                      // PIN display field
                      Container(
                        height: 48,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          border: Border.all(color: _errorMessage != null ? Colors.red : theme.dividerColor),
                          borderRadius: BorderRadius.circular(8),
                          color: theme.colorScheme.surface,
                        ),
                        child: Text(
                          _pin.isEmpty ? '••••' : '•' * _pin.length,
                          style: const TextStyle(fontSize: 24, letterSpacing: 8, fontWeight: FontWeight.bold),
                        ),
                      ),
                      if (_errorMessage != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 6.0),
                          child: Text(
                            _errorMessage!,
                            style: const TextStyle(color: Colors.red, fontSize: 12, fontWeight: FontWeight.bold),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      const SizedBox(height: 12),

                      // Numeric PIN Pad
                      PinPadWidget(
                        onKeyPress: _onKeyPress,
                        onClear: _onClear,
                        onEnter: _submitLogin,
                      ),
                      const SizedBox(height: 14),
                      const Divider(),

                      // Footer & Admin shortcut
                      Wrap(
                        alignment: WrapAlignment.spaceBetween,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text('Default PIN: 1234', style: TextStyle(fontSize: 12, color: Colors.grey[600])),
                          TextButton.icon(
                            icon: const Icon(Icons.admin_panel_settings, size: 16),
                            label: const Text('Admin Portal →', style: TextStyle(fontWeight: FontWeight.bold)),
                            onPressed: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => AdminScreen(posState: widget.posState),
                                ),
                              );
                            },
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
