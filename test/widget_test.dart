import 'package:flutter_test/flutter_test.dart';
import 'package:oraforge_pos/main.dart';
import 'package:oraforge_pos/state/pos_state.dart';
import 'package:oraforge_pos/models/business_profile.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Oraforge POS app boots up to staff login screen', (WidgetTester tester) async {
    final posState = PosState();
    await posState.init();

    await tester.pumpWidget(OraforgePosApp(posState: posState));
    await tester.pumpAndSettle();

    expect(find.text('Staff Access'), findsOneWidget);
    expect(find.text('1-Click Demo Login (PIN: 1234)'), findsOneWidget);
  });

  test('PosState supports all 6 profiles, cart management, and checkout', () async {
    final posState = PosState();
    await posState.init();

    // Verify all 6 profiles exist
    expect(BusinessProfile.allProfiles.length, 6);
    expect(BusinessProfile.getById('pharmacy').name, 'Pharmacy & Chemist');
    expect(BusinessProfile.getById('restaurant').name, 'Restaurant & Café');

    // Login to Pharmacy
    final success = await posState.login('pharmacy', '1234');
    expect(success, true);
    expect(posState.isLoggedIn, true);
    expect(posState.activeProfile.id, 'pharmacy');
    expect(posState.categories.isNotEmpty, true);
    expect(posState.products.isNotEmpty, true);

    // Add product to cart
    final product = posState.products.first;
    final initialStock = product.stockQty;
    posState.addToCart(product);
    expect(posState.cart.length, 1);
    expect(posState.cart.first.name, product.name);
    expect(posState.cartGrandTotal, product.price);

    // Checkout with M-Pesa
    final order = await posState.checkout(
      method: 'mpesa',
      paymentRef: 'MPESA-TEST-99',
      customerName: 'John Doe',
    );
    expect(order.status, 'paid');
    expect(order.paymentMethod, 'mpesa');
    expect(order.paymentRef, 'MPESA-TEST-99');
    expect(posState.cart.isEmpty, true);
    expect(posState.orders.length, 1);
    expect(posState.todayPaidCount, 1);
    expect(posState.todaySales, order.total);
    // Verify stock decreased
    expect(posState.products.first.stockQty, initialStock - 1);

    // Logout
    await posState.logout();
    expect(posState.isLoggedIn, false);
  });
}
