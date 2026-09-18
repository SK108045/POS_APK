import 'package:flutter/material.dart';
import 'state/pos_state.dart';
import 'screens/login_screen.dart';
import 'screens/home_shell.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final posState = PosState();
  await posState.init();

  runApp(OraforgePosApp(posState: posState));
}

class OraforgePosApp extends StatelessWidget {
  final PosState posState;

  const OraforgePosApp({super.key, required this.posState});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: posState,
      builder: (context, _) {
        return MaterialApp(
          title: 'Oraforge POS',
          debugShowCheckedModeBanner: false,
          themeMode: posState.isDarkMode ? ThemeMode.dark : ThemeMode.light,
          theme: ThemeData(
            useMaterial3: true,
            colorSchemeSeed: const Color(0xFF2563EB),
            brightness: Brightness.light,
            cardTheme: CardThemeData(
              elevation: 1,
              surfaceTintColor: Colors.transparent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            appBarTheme: const AppBarTheme(
              elevation: 0,
              centerTitle: false,
            ),
          ),
          darkTheme: ThemeData(
            useMaterial3: true,
            colorSchemeSeed: const Color(0xFF3B82F6),
            brightness: Brightness.dark,
            cardTheme: CardThemeData(
              elevation: 1,
              surfaceTintColor: Colors.transparent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            appBarTheme: const AppBarTheme(
              elevation: 0,
              centerTitle: false,
            ),
          ),
          home: posState.isLoggedIn
              ? HomeShell(posState: posState)
              : LoginScreen(posState: posState),
        );
      },
    );
  }
}
