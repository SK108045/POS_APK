import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../state/pos_state.dart';
import '../models/category.dart';
import '../models/product.dart';
import '../widgets/payment_dialog.dart';
import '../widgets/receipt_dialog.dart';
import 'admin_screen.dart';

class PosScreen extends StatefulWidget {
  final PosState posState;

  const PosScreen({super.key, required this.posState});

  @override
  State<PosScreen> createState() => _PosScreenState();
}

class _PosScreenState extends State<PosScreen> {
  int? _selectedCategoryId; // null = all
  String _searchQuery = '';
  final TextEditingController _searchCtrl = TextEditingController();

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  List<Product> get _filteredProducts {
    var list = widget.posState.products;
    if (_selectedCategoryId != null) {
      list = list.where((p) => p.categoryId == _selectedCategoryId).toList();
    }
    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      list = list.where((p) =>
          p.name.toLowerCase().contains(q) ||
          p.sku.toLowerCase().contains(q)).toList();
    }
    return list;
  }

  void _showCartSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _buildCartModal(ctx),
    );
  }

  void _openPaymentDialog() {
    if (widget.posState.cart.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cart is empty. Add items first.')),
      );
      return;
    }

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => PaymentDialog(
        totalAmount: widget.posState.cartGrandTotal,
        onPay: (method, ref, customer) async {
          final order = await widget.posState.checkout(
            method: method,
            paymentRef: ref,
            customerName: customer,
          );
          if (mounted) {
            showDialog(
              context: context,
              builder: (dCtx) => ReceiptDialog(
                order: order,
                shopName: '${widget.posState.activeProfile.name} POS',
                shopTagline: widget.posState.activeProfile.tagline,
              ),
            );
          }
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final currencyFmt = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    final profile = widget.posState.activeProfile;
    final cartCount = widget.posState.cart.fold<int>(0, (sum, i) => sum + i.qty);

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 12,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(profile.icon, style: const TextStyle(fontSize: 18)),
                  const SizedBox(width: 6),
                  Text(
                    profile.name,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w900,
                      color: theme.colorScheme.onPrimaryContainer,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'Terminal',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.admin_panel_settings_outlined),
            tooltip: 'Admin Portal',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => AdminScreen(posState: widget.posState)),
              );
            },
          ),
          IconButton(
            icon: Icon(widget.posState.isDarkMode ? Icons.light_mode : Icons.dark_mode),
            tooltip: 'Toggle Theme',
            onPressed: () => widget.posState.toggleTheme(),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout to switch store',
            onPressed: () => widget.posState.logout(),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Search Input
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
              child: TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                  hintText: 'Search ${profile.name} products or SKU...',
                  prefixIcon: const Icon(Icons.search, size: 20),
                  suffixIcon: _searchQuery.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, size: 18),
                          onPressed: () {
                            setState(() {
                              _searchCtrl.clear();
                              _searchQuery = '';
                            });
                          },
                        )
                      : null,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  isDense: true,
                ),
                onChanged: (val) {
                  setState(() {
                    _searchQuery = val.trim();
                  });
                },
              ),
            ),

            // Horizontal Category Chips
            SizedBox(
              height: 44,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                children: [
                  ChoiceChip(
                    label: const Text('All Items', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                    selected: _selectedCategoryId == null,
                    onSelected: (sel) {
                      if (sel) setState(() => _selectedCategoryId = null);
                    },
                  ),
                  const SizedBox(width: 6),
                  ...widget.posState.categories.map((cat) {
                    final isSel = _selectedCategoryId == cat.id;
                    return Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: Text(
                          '${cat.icon} ${cat.name}',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                        selected: isSel,
                        onSelected: (sel) {
                          setState(() {
                            _selectedCategoryId = sel ? cat.id : null;
                          });
                        },
                      ),
                    );
                  }),
                ],
              ),
            ),

            // Product Grid
            Expanded(
              child: _filteredProducts.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.inventory_2_outlined, size: 48, color: Colors.grey[400]),
                          const SizedBox(height: 8),
                          Text(
                            'No items match "$_searchQuery"',
                            style: TextStyle(color: Colors.grey[600]),
                          ),
                        ],
                      ),
                    )
                  : GridView.builder(
                      padding: const EdgeInsets.fromLTRB(12, 6, 12, 80),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        childAspectRatio: 0.82,
                        crossAxisSpacing: 10,
                        mainAxisSpacing: 10,
                      ),
                      itemCount: _filteredProducts.length,
                      itemBuilder: (ctx, idx) {
                        final product = _filteredProducts[idx];
                        return _buildProductCard(context, product, currencyFmt);
                      },
                    ),
            ),
          ],
        ),
      ),
      // Persistent Bottom Cart Bar
      bottomNavigationBar: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.08),
              blurRadius: 10,
              offset: const Offset(0, -3),
            ),
          ],
          border: Border(top: BorderSide(color: theme.dividerColor)),
        ),
        child: SafeArea(
          child: Row(
            children: [
              // Cart trigger button
              InkWell(
                onTap: _showCartSheet,
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.secondaryContainer,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      Badge(
                        label: Text('$cartCount'),
                        isLabelVisible: cartCount > 0,
                        child: const Icon(Icons.shopping_cart_outlined, size: 22),
                      ),
                      const SizedBox(width: 8),
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Ticket', style: TextStyle(fontSize: 10, color: Colors.grey)),
                          Text(
                            currencyFmt.format(widget.posState.cartGrandTotal),
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 10),
              // Charge Action
              Expanded(
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  icon: const Icon(Icons.payments, size: 20),
                  label: Text(
                    cartCount > 0
                        ? 'Charge ${currencyFmt.format(widget.posState.cartGrandTotal)}'
                        : 'Charge (0)',
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900),
                  ),
                  onPressed: cartCount > 0 ? _openPaymentDialog : null,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProductCard(
    BuildContext context,
    Product product,
    NumberFormat currencyFmt,
  ) {
    final theme = Theme.of(context);
    final inStock = product.stockQty > 0;

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: inStock ? Colors.transparent : Colors.red.withOpacity(0.3),
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: inStock
            ? () {
                widget.posState.addToCart(product);
                ScaffoldMessenger.of(context).clearSnackBars();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Added ${product.name} to cart'),
                    duration: const Duration(milliseconds: 700),
                    behavior: SnackBarBehavior.floating,
                  ),
                );
              }
            : null,
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Image / Placeholder area
              Expanded(
                child: Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceVariant.withOpacity(0.4),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Center(
                    child: Text(
                      _getCategoryIcon(product.categoryId),
                      style: const TextStyle(fontSize: 36),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              // Name
              Text(
                product.name,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 2),
              // SKU & Stock
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    product.sku,
                    style: TextStyle(fontSize: 10, color: Colors.grey[600]),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                    decoration: BoxDecoration(
                      color: inStock
                          ? (product.stockQty <= 10
                              ? Colors.orange.withOpacity(0.2)
                              : Colors.green.withOpacity(0.15))
                          : Colors.red.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      inStock ? '${product.stockQty} left' : 'Out of stock',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: inStock
                            ? (product.stockQty <= 10 ? Colors.orange[800] : Colors.green[800])
                            : Colors.red[800],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              // Price
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    currencyFmt.format(product.price),
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                      fontSize: 13,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Icon(Icons.add, size: 14, color: Colors.white),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _getCategoryIcon(int catId) {
    final cat = widget.posState.categories.firstWhere(
      (c) => c.id == catId,
      orElse: () => Category(id: 0, name: '', icon: '📦'),
    );
    return cat.icon;
  }

  Widget _buildCartModal(BuildContext context) {
    final theme = Theme.of(context);
    final currencyFmt = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);

    return StatefulBuilder(
      builder: (ctx, setModalState) {
        final cartItems = widget.posState.cart;

        return DraggableScrollableSheet(
          initialChildSize: 0.65,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          builder: (_, scrollController) {
            return Container(
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
              ),
              child: Column(
                children: [
                  // Handle
                  Container(
                    margin: const EdgeInsets.only(top: 8, bottom: 4),
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey[400],
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  // Header
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.receipt_long, size: 20),
                            const SizedBox(width: 8),
                            Text(
                              'Current Ticket (${cartItems.length} items)',
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                            ),
                          ],
                        ),
                        if (cartItems.isNotEmpty)
                          TextButton(
                            onPressed: () {
                              widget.posState.clearCart();
                              setModalState(() {});
                              setState(() {});
                            },
                            child: const Text('Clear', style: TextStyle(color: Colors.red)),
                          ),
                      ],
                    ),
                  ),
                  const Divider(height: 1),

                  // Cart Item List
                  Expanded(
                    child: cartItems.isEmpty
                        ? const Center(
                            child: Text('No items in current ticket',
                                style: TextStyle(color: Colors.grey)),
                          )
                        : ListView.separated(
                            controller: scrollController,
                            itemCount: cartItems.length,
                            separatorBuilder: (ctx, idx) => const Divider(height: 1),
                            itemBuilder: (c, i) {
                              final item = cartItems[i];
                              return ListTile(
                                dense: true,
                                title: Text(item.name,
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                subtitle: Text(
                                  '@ ${currencyFmt.format(item.unitPrice)} each',
                                  style: TextStyle(fontSize: 11, color: Colors.grey[600]),
                                ),
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    IconButton(
                                      icon: const Icon(Icons.remove_circle_outline, size: 20),
                                      onPressed: () {
                                        widget.posState.updateCartQty(i, -1);
                                        setModalState(() {});
                                        setState(() {});
                                      },
                                    ),
                                    Text(
                                      '${item.qty}',
                                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                    ),
                                    IconButton(
                                      icon: const Icon(Icons.add_circle_outline, size: 20),
                                      onPressed: () {
                                        widget.posState.updateCartQty(i, 1);
                                        setModalState(() {});
                                        setState(() {});
                                      },
                                    ),
                                    const SizedBox(width: 6),
                                    SizedBox(
                                      width: 70,
                                      child: Text(
                                        currencyFmt.format(item.lineTotal),
                                        textAlign: TextAlign.end,
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                  ),

                  // Summary & Charge footer
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceVariant.withOpacity(0.3),
                      border: Border(top: BorderSide(color: theme.dividerColor)),
                    ),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('Subtotal:'),
                            Text(currencyFmt.format(widget.posState.cartSubtotal),
                                style: const TextStyle(fontWeight: FontWeight.bold)),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('Tax (0%):'),
                            Text(currencyFmt.format(0), style: TextStyle(color: Colors.grey[600])),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('TOTAL AMOUNT:',
                                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                            Text(
                              currencyFmt.format(widget.posState.cartGrandTotal),
                              style: TextStyle(
                                fontWeight: FontWeight.w900,
                                fontSize: 18,
                                color: theme.colorScheme.primary,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            style: FilledButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                            icon: const Icon(Icons.payments),
                            label: const Text('Proceed to Payment',
                                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                            onPressed: cartItems.isEmpty
                                ? null
                                : () {
                                    Navigator.pop(context);
                                    _openPaymentDialog();
                                  },
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}
