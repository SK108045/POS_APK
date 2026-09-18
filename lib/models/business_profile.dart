class BusinessProfile {
  final String id;
  final String name;
  final String icon;
  final String tagline;
  final String itemLabel;

  const BusinessProfile({
    required this.id,
    required this.name,
    required this.icon,
    required this.tagline,
    this.itemLabel = 'Products',
  });

  static const List<BusinessProfile> allProfiles = [
    BusinessProfile(
      id: 'retail',
      name: 'Retail / Mini-Mart',
      icon: '🛒',
      tagline: 'Supermarket, Grocery & General Retail POS',
      itemLabel: 'Products',
    ),
    BusinessProfile(
      id: 'pharmacy',
      name: 'Pharmacy & Chemist',
      icon: '💊',
      tagline: 'Pharmacy, Chemist & Healthcare POS',
      itemLabel: 'Medicines',
    ),
    BusinessProfile(
      id: 'restaurant',
      name: 'Restaurant & Café',
      icon: '🍽️',
      tagline: 'Dine-in, Takeaway & Café POS',
      itemLabel: 'Menu Items',
    ),
    BusinessProfile(
      id: 'hardware',
      name: 'Hardware & Tools',
      icon: '🔧',
      tagline: 'Building Supplies, Tools & Hardware POS',
      itemLabel: 'Materials',
    ),
    BusinessProfile(
      id: 'boutique',
      name: 'Boutique & Fashion',
      icon: '👗',
      tagline: 'Clothing, Apparel & Cosmetics POS',
      itemLabel: 'Apparel',
    ),
    BusinessProfile(
      id: 'bar',
      name: 'Bar & Nightclub',
      icon: '🍸',
      tagline: 'Bar, Lounge, Pub & Club POS',
      itemLabel: 'Drinks',
    ),
  ];

  static BusinessProfile getById(String id) {
    return allProfiles.firstWhere(
      (p) => p.id == id,
      orElse: () => allProfiles.first,
    );
  }
}
