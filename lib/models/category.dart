class Category {
  final int id;
  final String name;
  final int sortOrder;
  final String businessType;
  final String icon;

  const Category({
    required this.id,
    required this.name,
    this.sortOrder = 0,
    this.businessType = 'retail',
    this.icon = '🏷️',
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'sort_order': sortOrder,
        'business_type': businessType,
        'icon': icon,
      };

  factory Category.fromJson(Map<String, dynamic> json) => Category(
        id: json['id'] as int,
        name: json['name'] as String,
        sortOrder: json['sort_order'] as int? ?? 0,
        businessType: json['business_type'] as String? ?? 'retail',
        icon: json['icon'] as String? ?? '🏷️',
      );
}
