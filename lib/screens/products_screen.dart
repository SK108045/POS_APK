import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../state/pos_state.dart';
import '../models/category.dart';
import '../models/product.dart';

class ProductsScreen extends StatefulWidget {
  final PosState posState;

  const ProductsScreen({super.key, required this.posState});

  @override
  State<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends State<ProductsScreen> {
  int? _selectedCategory;
  String _search = '';
  final TextEditingController _searchCtrl = TextEditingController();

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  List<Product> get _filteredProducts {
    var list = widget.posState.products;
    if (_selectedCategory != null) {
      list = list.where((p) => p.categoryId == _selectedCategory).toList();
    }
    if (_search.isNotEmpty) {
      final s = _search.toLowerCase();
      list = list.where((p) =>
          p.name.toLowerCase().contains(s) ||
          p.sku.toLowerCase().contains(s)).toList();
    }
    return list;
  }

  @override
  Widget build(BuildContext context) {
    final currencyFmt = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    final theme = Theme.of(context);
    final products = widget.posState.products;
    final totalInventoryCents = products.fold(0, (sum, p) => sum + (p.priceCents * p.stockQty));
    final lowStockCount = products.where((p) => p.stockQty <= 10).length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Inventory Catalog'),
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Inventory Stat Banner
            Container(
              margin: const EdgeInsets.fromLTRB(16, 10, 16, 6),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceVariant.withOpacity(0.4),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: theme.dividerColor),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Column(
                    children: [
                      const Text('Total Items', style: TextStyle(fontSize: 11, color: Colors.grey)),
                      Text('${products.length}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  Container(height: 24, width: 1, color: Colors.grey[400]),
                  Column(
                    children: [
                      const Text('Total Stock Value', style: TextStyle(fontSize: 11, color: Colors.grey)),
                      Text(currencyFmt.format(totalInventoryCents / 100),
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: theme.colorScheme.primary)),
                    ],
                  ),
                  Container(height: 24, width: 1, color: Colors.grey[400]),
                  Column(
                    children: [
                      const Text('Low Stock', style: TextStyle(fontSize: 11, color: Colors.grey)),
                      Text('$lowStockCount',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: lowStockCount > 0 ? Colors.orange[800] : Colors.green[800],
                          )),
                    ],
                  ),
                ],
              ),
            ),

            // Search Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                  hintText: 'Search inventory by name or SKU...',
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

            // Category filter chips
            SizedBox(
              height: 40,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                children: [
                  ChoiceChip(
                    label: const Text('All Categories'),
                    selected: _selectedCategory == null,
                    onSelected: (s) {
                      if (s) setState(() => _selectedCategory = null);
                    },
                  ),
                  const SizedBox(width: 8),
                  ...widget.posState.categories.map((c) {
                    final isSel = _selectedCategory == c.id;
                    return Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: Text('${c.icon} ${c.name}'),
                        selected: isSel,
                        onSelected: (s) {
                          setState(() => _selectedCategory = s ? c.id : null);
                        },
                      ),
                    );
                  }),
                ],
              ),
            ),
            const SizedBox(height: 8),

            // Products list
            Expanded(
              child: _filteredProducts.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.inventory_2_outlined, size: 48, color: Colors.grey[400]),
                          const SizedBox(height: 8),
                          Text('No matching inventory found', style: TextStyle(color: Colors.grey[600])),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      itemCount: _filteredProducts.length,
                      itemBuilder: (ctx, i) {
                        final product = _filteredProducts[i];
                        final inStock = product.stockQty > 0;
                        final isLow = product.stockQty > 0 && product.stockQty <= 10;

                        return Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Row(
                              children: [
                                Container(
                                  width: 44,
                                  height: 44,
                                  decoration: BoxDecoration(
                                    color: theme.colorScheme.primaryContainer.withOpacity(0.5),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Center(
                                    child: Text(
                                      _getCategoryIcon(product.categoryId),
                                      style: const TextStyle(fontSize: 22),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        product.name,
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        'SKU: ${product.sku} • Unit: ${product.unit}',
                                        style: TextStyle(fontSize: 11, color: Colors.grey[600]),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        currencyFmt.format(product.price),
                                        style: TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13,
                                          color: theme.colorScheme.primary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                      decoration: BoxDecoration(
                                        color: !inStock
                                            ? Colors.red.withOpacity(0.15)
                                            : (isLow ? Colors.orange.withOpacity(0.15) : Colors.green.withOpacity(0.15)),
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: Text(
                                        !inStock
                                            ? 'Out of Stock'
                                            : '${product.stockQty} ${product.unit}',
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.bold,
                                          color: !inStock
                                              ? Colors.red[800]
                                              : (isLow ? Colors.orange[800] : Colors.green[800]),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(height: 6),
                                    // Stock adjustment buttons
                                    Row(
                                      children: [
                                        InkWell(
                                          borderRadius: BorderRadius.circular(4),
                                          onTap: () {
                                            setState(() {
                                              product.stockQty = (product.stockQty - 1).clamp(0, 999999);
                                            });
                                          },
                                          child: Container(
                                            padding: const EdgeInsets.all(4),
                                            decoration: BoxDecoration(
                                              border: Border.all(color: Colors.grey[400]!),
                                              borderRadius: BorderRadius.circular(4),
                                            ),
                                            child: const Icon(Icons.remove, size: 14),
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        InkWell(
                                          borderRadius: BorderRadius.circular(4),
                                          onTap: () {
                                            setState(() {
                                              product.stockQty += 10;
                                            });
                                          },
                                          child: Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                                            decoration: BoxDecoration(
                                              color: theme.colorScheme.primaryContainer,
                                              borderRadius: BorderRadius.circular(4),
                                            ),
                                            child: const Text('+10',
                                                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ],
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

  String _getCategoryIcon(int catId) {
    final cat = widget.posState.categories.firstWhere(
      (c) => c.id == catId,
      orElse: () => Category(id: 0, name: '', icon: '📦'),
    );
    return cat.icon;
  }
}
