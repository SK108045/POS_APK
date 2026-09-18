class Product {
  final int id;
  final int categoryId;
  final String name;
  final int priceCents;
  final int costCents;
  final String color;
  final String sku;
  final String barcode;
  int stockQty;
  final String unit;
  final String imageUrl;

  Product({
    required this.id,
    required this.categoryId,
    required this.name,
    required this.priceCents,
    this.costCents = 0,
    this.color = '#334155',
    this.sku = '',
    this.barcode = '',
    this.stockQty = 100,
    this.unit = 'pcs',
    this.imageUrl = '',
  });

  double get price => priceCents / 100.0;
  double get cost => costCents / 100.0;

  Map<String, dynamic> toJson() => {
        'id': id,
        'category_id': categoryId,
        'name': name,
        'price_cents': priceCents,
        'cost_cents': costCents,
        'color': color,
        'sku': sku,
        'barcode': barcode,
        'stock_qty': stockQty,
        'unit': unit,
        'image_url': imageUrl,
      };

  factory Product.fromJson(Map<String, dynamic> json) => Product(
        id: json['id'] as int,
        categoryId: json['category_id'] as int,
        name: json['name'] as String,
        priceCents: json['price_cents'] as int,
        costCents: json['cost_cents'] as int? ?? 0,
        color: json['color'] as String? ?? '#334155',
        sku: json['sku'] as String? ?? '',
        barcode: json['barcode'] as String? ?? '',
        stockQty: json['stock_qty'] as int? ?? 0,
        unit: json['unit'] as String? ?? 'pcs',
        imageUrl: json['image_url'] as String? ?? '',
      );
}
