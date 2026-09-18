import 'package:flutter/material.dart';
import '../state/pos_state.dart';
import 'admin_screen.dart';

class SettingsScreen extends StatelessWidget {
  final PosState posState;

  const SettingsScreen({super.key, required this.posState});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final profile = posState.activeProfile;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Terminal Settings'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Active Store Card (Read-only as required)
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('CURRENT BUSINESS PROFILE',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.grey)),
                        Icon(Icons.lock_outline, size: 16, color: Colors.grey),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            color: theme.colorScheme.primaryContainer,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Center(
                            child: Text(profile.icon, style: const TextStyle(fontSize: 26)),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(profile.name,
                                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
                              Text(profile.tagline,
                                  style: TextStyle(fontSize: 12, color: Colors.grey[600])),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.amber.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.amber.withOpacity(0.3)),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.info_outline, size: 18, color: Colors.amber),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Store category is locked during active shift. To switch store, log out to the staff login screen.',
                              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
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

            // Admin Portal Access Button
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              color: theme.colorScheme.secondaryContainer.withOpacity(0.5),
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: theme.colorScheme.primary,
                  child: const Icon(Icons.admin_panel_settings, color: Colors.white),
                ),
                title: const Text('Admin Management Portal',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                subtitle: const Text('Access store controls, KPI metrics, and staff authorizations'),
                trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => AdminScreen(posState: posState)),
                  );
                },
              ),
            ),
            const SizedBox(height: 16),

            // Preferences
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              child: Column(
                children: [
                  SwitchListTile(
                    secondary: Icon(posState.isDarkMode ? Icons.dark_mode : Icons.light_mode),
                    title: const Text('Dark Mode Theme'),
                    subtitle: const Text('Optimize interface for low-light environments'),
                    value: posState.isDarkMode,
                    onChanged: (_) => posState.toggleTheme(),
                  ),
                  const Divider(height: 1),
                  const ListTile(
                    leading: Icon(Icons.attach_money),
                    title: Text('Operating Currency'),
                    subtitle: Text('Kenyan Shilling (KES)'),
                    trailing: Text('KES', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                  const Divider(height: 1),
                  const ListTile(
                    leading: Icon(Icons.print_outlined),
                    title: Text('Thermal Receipt Printer'),
                    subtitle: Text('Default: 58mm / 80mm ESC/POS'),
                    trailing: Text('Ready', style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Logout Button
            FilledButton.tonalIcon(
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              icon: const Icon(Icons.logout, color: Colors.red),
              label: const Text(
                'Log Out Shift (Switch Store)',
                style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold, fontSize: 15),
              ),
              onPressed: () async {
                final confirm = await showDialog<bool>(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('End Shift & Logout?'),
                    content: const Text(
                      'You will return to the Login screen where you can select another store profile.',
                    ),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                      FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Logout')),
                    ],
                  ),
                );
                if (confirm == true) {
                  await posState.logout();
                }
              },
            ),
            const SizedBox(height: 12),
            Center(
              child: Text(
                'Oraforge POS v2.0 (Flutter Native)',
                style: TextStyle(fontSize: 12, color: Colors.grey[500]),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
