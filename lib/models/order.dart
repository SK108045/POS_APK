class OrderItem {
  final int id;
  final int menuItemId;
  final String name;
  int qty;
  final int unitPriceCents;
  final String note;

  OrderItem({
    required this.id,
    required this.menuItemId,
    required this.name,
    required this.qty,
    required this.unitPriceCents,
    this.note = '',
  });

  int get lineTotalCents => unitPriceCents * qty;
  double get unitPrice => unitPriceCents / 100.0;
  double get lineTotal => lineTotalCents / 100.0;

  Map<String, dynamic> toJson() => {
        'id': id,
        'menu_item_id': menuItemId,
        'name': name,
        'qty': qty,
        'unit_price_cents': unitPriceCents,
        'line_total_cents': lineTotalCents,
        'note': note,
      };

  factory OrderItem.fromJson(Map<String, dynamic> json) => OrderItem(
        id: json['id'] as int,
        menuItemId: json['menu_item_id'] as int,
        name: json['name'] as String,
        qty: json['qty'] as int? ?? 1,
        unitPriceCents: json['unit_price_cents'] as int,
        note: json['note'] as String? ?? '',
      );
}

class Order {
  final int id;
  final String ticketNo;
  final String orderType;
  final String customerName;
  String status;
  final int subtotalCents;
  final int taxCents;
  final int totalCents;
  int paidCents;
  String paymentMethod;
  String paymentRef;
  final int createdAt;
  int paidAt;
  final List<OrderItem> items;

  Order({
    required this.id,
    required this.ticketNo,
    this.orderType = 'walk-in',
    this.customerName = '',
    this.status = 'open',
    required this.subtotalCents,
    this.taxCents = 0,
    required this.totalCents,
    this.paidCents = 0,
    this.paymentMethod = 'cash',
    this.paymentRef = '',
    required this.createdAt,
    this.paidAt = 0,
    required this.items,
  });

  double get subtotal => subtotalCents / 100.0;
  double get tax => taxCents / 100.0;
  double get total => totalCents / 100.0;
  double get paid => paidCents / 100.0;

  Map<String, dynamic> toJson() => {
        'id': id,
        'ticket_no': ticketNo,
        'order_type': orderType,
        'customer_name': customerName,
        'status': status,
        'subtotal_cents': subtotalCents,
        'tax_cents': taxCents,
        'total_cents': totalCents,
        'paid_cents': paidCents,
        'payment_method': paymentMethod,
        'payment_ref': paymentRef,
        'created_at': createdAt,
        'paid_at': paidAt,
        'items': items.map((i) => i.toJson()).toList(),
      };

  factory Order.fromJson(Map<String, dynamic> json) => Order(
        id: json['id'] as int,
        ticketNo: json['ticket_no'] as String,
        orderType: json['order_type'] as String? ?? 'walk-in',
        customerName: json['customer_name'] as String? ?? '',
        status: json['status'] as String? ?? 'open',
        subtotalCents: json['subtotal_cents'] as int,
        taxCents: json['tax_cents'] as int? ?? 0,
        totalCents: json['total_cents'] as int,
        paidCents: json['paid_cents'] as int? ?? 0,
        paymentMethod: json['payment_method'] as String? ?? 'cash',
        paymentRef: json['payment_ref'] as String? ?? '',
        createdAt: json['created_at'] as int,
        paidAt: json['paid_at'] as int? ?? 0,
        items: (json['items'] as List<dynamic>?)
                ?.map((i) => OrderItem.fromJson(i as Map<String, dynamic>))
                .toList() ??
            [],
      );
}
