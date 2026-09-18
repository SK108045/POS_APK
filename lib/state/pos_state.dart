import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/business_profile.dart';
import '../models/category.dart';
import '../models/product.dart';
import '../models/order.dart';
import '../data/sample_catalogs.dart';

class PosState extends ChangeNotifier {
  bool _isLoggedIn = false;
  BusinessProfile _activeProfile = BusinessProfile.allProfiles.first;
  bool _isDarkMode = false;

  List<Category> _categories = [];
  List<Product> _products = [];
  final List<OrderItem> _cart = [];
  List<Order> _orders = [];

  bool get isLoggedIn => _isLoggedIn;
  BusinessProfile get activeProfile => _activeProfile;
  bool get isDarkMode => _isDarkMode;

  List<Category> get categories => List.unmodifiable(_categories);
  List<Product> get products => List.unmodifiable(_products);
  List<OrderItem> get cart => List.unmodifiable(_cart);
  List<Order> get orders => List.unmodifiable(_orders);

  int get cartSubtotalCents => _cart.fold(0, (sum, i) => sum + i.lineTotalCents);
  double get cartSubtotal => cartSubtotalCents / 100.0;
  double get cartGrandTotal => cartSubtotal; // 0% tax or inclusive

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _isLoggedIn = prefs.getBool('pos_logged_in') ?? false;
    _isDarkMode = prefs.getBool('pos_dark_theme') ?? false;
    final savedProfileId = prefs.getString('pos_profile_id') ?? 'retail';
    _activeProfile = BusinessProfile.getById(savedProfileId);

    // Load orders
    final ordersJson = prefs.getString('pos_orders');
    if (ordersJson != null) {
      try {
        final List<dynamic> list = jsonDecode(ordersJson);
        _orders = list.map((o) => Order.fromJson(o as Map<String, dynamic>)).toList();
      } catch (_) {}
    }

    _loadCatalogForProfile(_activeProfile.id);
    notifyListeners();
  }

  void _loadCatalogForProfile(String profileId) {
    final allCats = SampleCatalogs.getCategories();
    final allProds = SampleCatalogs.getProducts();

    _categories = allCats[profileId] ?? allCats['retail']!;
    _products = allProds[profileId] ?? allProds['retail']!;
  }

  Future<bool> login(String profileId, String pin) async {
    if (pin != '1234' && pin.length < 4) {
      return false;
    }
    _activeProfile = BusinessProfile.getById(profileId);
    _isLoggedIn = true;
    _cart.clear();
    _loadCatalogForProfile(_activeProfile.id);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('pos_logged_in', true);
    await prefs.setString('pos_profile_id', _activeProfile.id);

    notifyListeners();
    return true;
  }

  Future<void> logout() async {
    _isLoggedIn = false;
    _cart.clear();

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('pos_logged_in', false);

    notifyListeners();
  }

  Future<void> toggleTheme() async {
    _isDarkMode = !_isDarkMode;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('pos_dark_theme', _isDarkMode);
    notifyListeners();
  }

  void addToCart(Product product) {
    final existingIndex = _cart.indexWhere((item) => item.menuItemId == product.id);
    if (existingIndex >= 0) {
      _cart[existingIndex].qty += 1;
    } else {
      _cart.add(OrderItem(
        id: _cart.length + 1,
        menuItemId: product.id,
        name: product.name,
        qty: 1,
        unitPriceCents: product.priceCents,
      ));
    }
    notifyListeners();
  }

  void updateCartQty(int index, int delta) {
    if (index >= 0 && index < _cart.length) {
      _cart[index].qty += delta;
      if (_cart[index].qty <= 0) {
        _cart.removeAt(index);
      }
      notifyListeners();
    }
  }

  void removeFromCart(int index) {
    if (index >= 0 && index < _cart.length) {
      _cart.removeAt(index);
      notifyListeners();
    }
  }

  void clearCart() {
    _cart.clear();
    notifyListeners();
  }

  Future<Order> checkout({
    required String method,
    required String paymentRef,
    String customerName = '',
  }) async {
    final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    final ticketNo = 'R$now${(_orders.length + 1).toString().padLeft(3, '0')}';
    final totalCents = cartSubtotalCents;

    final orderItems = _cart
        .map((i) => OrderItem(
              id: i.id,
              menuItemId: i.menuItemId,
              name: i.name,
              qty: i.qty,
              unitPriceCents: i.unitPriceCents,
              note: i.note,
            ))
        .toList();

    final newOrder = Order(
      id: _orders.length + 1,
      ticketNo: ticketNo,
      orderType: 'walk-in',
      customerName: customerName,
      status: 'paid',
      subtotalCents: totalCents,
      totalCents: totalCents,
      paidCents: totalCents,
      paymentMethod: method,
      paymentRef: paymentRef,
      createdAt: now,
      paidAt: now,
      items: orderItems,
    );

    // Decrement stock in catalog
    for (final cartItem in _cart) {
      final productIndex = _products.indexWhere((p) => p.id == cartItem.menuItemId);
      if (productIndex >= 0) {
        _products[productIndex].stockQty =
            (_products[productIndex].stockQty - cartItem.qty).clamp(0, 999999);
      }
    }

    _orders.insert(0, newOrder);
    _cart.clear();

    // Persist orders
    final prefs = await SharedPreferences.getInstance();
    final jsonList = _orders.map((o) => o.toJson()).toList();
    await prefs.setString('pos_orders', jsonEncode(jsonList));

    notifyListeners();
    return newOrder;
  }

  // Analytics
  double get todaySales {
    return _orders
        .where((o) => o.status == 'paid')
        .fold(0.0, (sum, o) => sum + o.total);
  }

  int get todayPaidCount {
    return _orders.where((o) => o.status == 'paid').length;
  }

  Map<String, double> get salesByMethod {
    final Map<String, double> result = {'cash': 0.0, 'mpesa': 0.0};
    for (final o in _orders.where((o) => o.status == 'paid')) {
      final method = o.paymentMethod.toLowerCase();
      result[method] = (result[method] ?? 0.0) + o.total;
    }
    return result;
  }
}
