import '../models/category.dart';
import '../models/product.dart';

class SampleCatalogs {
  static Map<String, List<Category>> getCategories() {
    return {
      'retail': [
        const Category(id: 1, name: 'Groceries', sortOrder: 0, businessType: 'retail', icon: '🛒'),
        const Category(id: 2, name: 'Beverages', sortOrder: 1, businessType: 'retail', icon: '🥤'),
        const Category(id: 3, name: 'Dairy & Bakery', sortOrder: 2, businessType: 'retail', icon: '🍞'),
        const Category(id: 4, name: 'Snacks & Sweets', sortOrder: 3, businessType: 'retail', icon: '🍫'),
        const Category(id: 5, name: 'Household', sortOrder: 4, businessType: 'retail', icon: '🧼'),
      ],
      'pharmacy': [
        const Category(id: 11, name: 'Prescription', sortOrder: 0, businessType: 'pharmacy', icon: '💊'),
        const Category(id: 12, name: 'OTC Pain Relief', sortOrder: 1, businessType: 'pharmacy', icon: '🩹'),
        const Category(id: 13, name: 'Antibiotics', sortOrder: 2, businessType: 'pharmacy', icon: '🧪'),
        const Category(id: 14, name: 'Cold & Cough', sortOrder: 3, businessType: 'pharmacy', icon: '🌡️'),
        const Category(id: 15, name: 'Vitamins & First Aid', sortOrder: 4, businessType: 'pharmacy', icon: '💉'),
      ],
      'restaurant': [
        const Category(id: 21, name: 'Breakfast & Starters', sortOrder: 0, businessType: 'restaurant', icon: '🥞'),
        const Category(id: 22, name: 'Main Courses', sortOrder: 1, businessType: 'restaurant', icon: '🍗'),
        const Category(id: 23, name: 'Burgers & Wraps', sortOrder: 2, businessType: 'restaurant', icon: '🍔'),
        const Category(id: 24, name: 'Pizza', sortOrder: 3, businessType: 'restaurant', icon: '🍕'),
        const Category(id: 25, name: 'Hot & Cold Drinks', sortOrder: 4, businessType: 'restaurant', icon: '☕'),
      ],
      'hardware': [
        const Category(id: 31, name: 'Power & Hand Tools', sortOrder: 0, businessType: 'hardware', icon: '🔨'),
        const Category(id: 32, name: 'Building & Cement', sortOrder: 1, businessType: 'hardware', icon: '🧱'),
        const Category(id: 33, name: 'Electrical & Cables', sortOrder: 2, businessType: 'hardware', icon: '⚡'),
        const Category(id: 34, name: 'Plumbing & Pipes', sortOrder: 3, businessType: 'hardware', icon: '🔧'),
        const Category(id: 35, name: 'Paints & Fasteners', sortOrder: 4, businessType: 'hardware', icon: '🎨'),
      ],
      'boutique': [
        const Category(id: 41, name: "Women's Fashion", sortOrder: 0, businessType: 'boutique', icon: '👗'),
        const Category(id: 42, name: "Men's Apparel", sortOrder: 1, businessType: 'boutique', icon: '👔'),
        const Category(id: 43, name: 'Denim & Jeans', sortOrder: 2, businessType: 'boutique', icon: '👖'),
        const Category(id: 44, name: 'Cosmetics & Skincare', sortOrder: 3, businessType: 'boutique', icon: '💄'),
        const Category(id: 45, name: 'Accessories', sortOrder: 4, businessType: 'boutique', icon: '👜'),
      ],
      'bar': [
        const Category(id: 51, name: 'Beers & Ciders', sortOrder: 0, businessType: 'bar', icon: '🍺'),
        const Category(id: 52, name: 'Craft Cocktails', sortOrder: 1, businessType: 'bar', icon: '🍸'),
        const Category(id: 53, name: 'Premium Spirits', sortOrder: 2, businessType: 'bar', icon: '🥃'),
        const Category(id: 54, name: 'Fine Wines', sortOrder: 3, businessType: 'bar', icon: '🍷'),
        const Category(id: 55, name: 'Soft Drinks', sortOrder: 4, businessType: 'bar', icon: '🥤'),
        const Category(id: 56, name: 'Bar Snacks', sortOrder: 5, businessType: 'bar', icon: '🥜'),
      ],
    };
  }

  static Map<String, List<Product>> getProducts() {
    return {
      'retail': [
        Product(id: 101, categoryId: 1, name: 'White Sugar 1kg', priceCents: 16000, costCents: 13000, color: '#f59e0b', sku: 'RET-001', stockQty: 80, unit: 'kg'),
        Product(id: 102, categoryId: 1, name: 'Basmati Rice 2kg', priceCents: 38000, costCents: 30000, color: '#eab308', sku: 'RET-002', stockQty: 50, unit: 'bag'),
        Product(id: 103, categoryId: 1, name: 'Cooking Oil 1L', priceCents: 29000, costCents: 24000, color: '#d97706', sku: 'RET-003', stockQty: 45, unit: 'btl'),
        Product(id: 104, categoryId: 2, name: 'Coca Cola 500ml', priceCents: 7000, costCents: 4500, color: '#dc2626', sku: 'RET-004', stockQty: 120, unit: 'btl'),
        Product(id: 105, categoryId: 2, name: 'Mineral Water 1L', priceCents: 6000, costCents: 3500, color: '#0ea5e9', sku: 'RET-005', stockQty: 90, unit: 'btl'),
        Product(id: 106, categoryId: 3, name: 'Fresh Milk 500ml', priceCents: 6500, costCents: 5000, color: '#3b82f6', sku: 'RET-006', stockQty: 40, unit: 'pkt'),
        Product(id: 107, categoryId: 3, name: 'Sliced Bread 400g', priceCents: 7500, costCents: 5800, color: '#b45309', sku: 'RET-007', stockQty: 30, unit: 'loaf'),
        Product(id: 108, categoryId: 4, name: 'Potato Crisps 50g', priceCents: 5000, costCents: 3500, color: '#f97316', sku: 'RET-008', stockQty: 75, unit: 'pkt'),
        Product(id: 109, categoryId: 5, name: 'Laundry Bar Soap', priceCents: 12000, costCents: 8500, color: '#16a34a', sku: 'RET-009', stockQty: 60, unit: 'bar'),
      ],
      'pharmacy': [
        Product(id: 201, categoryId: 12, name: 'Paracetamol 500mg (Tabs)', priceCents: 5000, costCents: 2000, color: '#ef4444', sku: 'PHA-001', stockQty: 200, unit: 'strip'),
        Product(id: 202, categoryId: 12, name: 'Ibuprofen 400mg', priceCents: 12000, costCents: 6500, color: '#f97316', sku: 'PHA-002', stockQty: 150, unit: 'box'),
        Product(id: 203, categoryId: 13, name: 'Amoxicillin 500mg', priceCents: 25000, costCents: 14000, color: '#3b82f6', sku: 'PHA-003', stockQty: 80, unit: 'strip'),
        Product(id: 204, categoryId: 14, name: 'Cough Syrup 100ml', priceCents: 35000, costCents: 21000, color: '#8b5cf6', sku: 'PHA-004', stockQty: 45, unit: 'btl'),
        Product(id: 205, categoryId: 14, name: 'Cetirizine 10mg', priceCents: 8000, costCents: 4000, color: '#06b6d4', sku: 'PHA-005', stockQty: 110, unit: 'strip'),
        Product(id: 206, categoryId: 15, name: 'Multivitamin Formula', priceCents: 65000, costCents: 42000, color: '#10b981', sku: 'PHA-006', stockQty: 35, unit: 'btl'),
        Product(id: 207, categoryId: 15, name: 'Iodine Antiseptic 50ml', priceCents: 15000, costCents: 8000, color: '#d97706', sku: 'PHA-007', stockQty: 60, unit: 'btl'),
      ],
      'restaurant': [
        Product(id: 301, categoryId: 21, name: 'Chicken Wings (6pcs)', priceCents: 65000, costCents: 35000, color: '#f59e0b', sku: 'RES-001', stockQty: 50, unit: 'portion'),
        Product(id: 302, categoryId: 22, name: 'Grilled Chicken & Chips', priceCents: 85000, costCents: 45000, color: '#ef4444', sku: 'RES-002', stockQty: 40, unit: 'plate'),
        Product(id: 303, categoryId: 22, name: 'Beef Stew with Rice', priceCents: 75000, costCents: 40000, color: '#b45309', sku: 'RES-003', stockQty: 35, unit: 'plate'),
        Product(id: 304, categoryId: 23, name: 'Classic Beef Burger', priceCents: 60000, costCents: 28000, color: '#d97706', sku: 'RES-004', stockQty: 60, unit: 'pcs'),
        Product(id: 305, categoryId: 23, name: 'Crispy Chicken Burger', priceCents: 65000, costCents: 30000, color: '#f97316', sku: 'RES-005', stockQty: 55, unit: 'pcs'),
        Product(id: 306, categoryId: 24, name: 'BBQ Chicken Pizza Large', priceCents: 120000, costCents: 60000, color: '#e11d48', sku: 'RES-006', stockQty: 30, unit: 'pie'),
        Product(id: 307, categoryId: 24, name: 'Margherita Pizza Large', priceCents: 100000, costCents: 48000, color: '#16a34a', sku: 'RES-007', stockQty: 25, unit: 'pie'),
        Product(id: 308, categoryId: 25, name: 'Espresso / Cappuccino', priceCents: 25000, costCents: 8000, color: '#78350f', sku: 'RES-008', stockQty: 999, unit: 'cup'),
      ],
      'hardware': [
        Product(id: 401, categoryId: 31, name: 'Claw Hammer 16oz', priceCents: 75000, costCents: 45000, color: '#475569', sku: 'HDW-001', stockQty: 30, unit: 'pcs'),
        Product(id: 402, categoryId: 31, name: 'Measuring Tape 5M', priceCents: 35000, costCents: 18000, color: '#eab308', sku: 'HDW-002', stockQty: 50, unit: 'pcs'),
        Product(id: 403, categoryId: 32, name: 'Portland Cement 50kg', priceCents: 85000, costCents: 75000, color: '#64748b', sku: 'HDW-003', stockQty: 100, unit: 'bag'),
        Product(id: 404, categoryId: 33, name: 'Twin & Earth Cable 50M', priceCents: 320000, costCents: 240000, color: '#0284c7', sku: 'HDW-004', stockQty: 20, unit: 'roll'),
        Product(id: 405, categoryId: 34, name: 'PPR Pipe 32mm 4M', priceCents: 65000, costCents: 42000, color: '#16a34a', sku: 'HDW-005', stockQty: 40, unit: 'pcs'),
        Product(id: 406, categoryId: 35, name: 'Emulsion Paint 4L White', priceCents: 180000, costCents: 130000, color: '#f8fafc', sku: 'HDW-006', stockQty: 25, unit: 'tin'),
        Product(id: 407, categoryId: 35, name: 'Assorted Steel Nails 1kg', priceCents: 18000, costCents: 11000, color: '#334155', sku: 'HDW-007', stockQty: 80, unit: 'kg'),
      ],
      'boutique': [
        Product(id: 501, categoryId: 41, name: 'Floral Summer Dress', priceCents: 250000, costCents: 140000, color: '#ec4899', sku: 'BOU-001', stockQty: 20, unit: 'pcs'),
        Product(id: 502, categoryId: 41, name: 'Silk Blouse White', priceCents: 180000, costCents: 100000, color: '#f43f5e', sku: 'BOU-002', stockQty: 25, unit: 'pcs'),
        Product(id: 503, categoryId: 42, name: 'Formal Cotton Shirt', priceCents: 190000, costCents: 110000, color: '#0284c7', sku: 'BOU-003', stockQty: 30, unit: 'pcs'),
        Product(id: 504, categoryId: 43, name: 'Slim Fit Denim Jeans', priceCents: 280000, costCents: 160000, color: '#1e3a8a', sku: 'BOU-004', stockQty: 35, unit: 'pcs'),
        Product(id: 505, categoryId: 44, name: 'Matte Liquid Lipstick', priceCents: 95000, costCents: 45000, color: '#be123c', sku: 'BOU-005', stockQty: 45, unit: 'pcs'),
        Product(id: 506, categoryId: 44, name: 'Vitamin C Facial Serum', priceCents: 160000, costCents: 85000, color: '#f59e0b', sku: 'BOU-006', stockQty: 30, unit: 'btl'),
      ],
      'bar': [
        Product(id: 601, categoryId: 51, name: 'Tusker Lager 500ml', priceCents: 25000, costCents: 20000, color: '#d97706', sku: 'BAR-001', stockQty: 120, unit: 'btl'),
        Product(id: 602, categoryId: 51, name: 'Guinness 500ml', priceCents: 30000, costCents: 24000, color: '#1e293b', sku: 'BAR-002', stockQty: 80, unit: 'btl'),
        Product(id: 603, categoryId: 51, name: 'White Cap 500ml', priceCents: 25000, costCents: 20000, color: '#94a3b8', sku: 'BAR-003', stockQty: 90, unit: 'btl'),
        Product(id: 604, categoryId: 51, name: 'Heineken 330ml', priceCents: 35000, costCents: 28000, color: '#15803d', sku: 'BAR-004', stockQty: 60, unit: 'btl'),
        Product(id: 605, categoryId: 52, name: 'Classic Mojito', priceCents: 60000, costCents: 25000, color: '#22c55e', sku: 'BAR-005', stockQty: 999, unit: 'glass'),
        Product(id: 606, categoryId: 52, name: 'Margarita Cocktail', priceCents: 65000, costCents: 28000, color: '#eab308', sku: 'BAR-006', stockQty: 999, unit: 'glass'),
        Product(id: 607, categoryId: 53, name: 'Jameson Irish Whiskey 750ml', priceCents: 350000, costCents: 270000, color: '#166534', sku: 'BAR-007', stockQty: 15, unit: 'btl'),
        Product(id: 608, categoryId: 53, name: 'Gilbeys Special Dry Gin', priceCents: 180000, costCents: 135000, color: '#0284c7', sku: 'BAR-008', stockQty: 18, unit: 'btl'),
        Product(id: 609, categoryId: 54, name: 'Four Cousins Natural Sweet', priceCents: 120000, costCents: 90000, color: '#9d174d', sku: 'BAR-009', stockQty: 25, unit: 'btl'),
        Product(id: 610, categoryId: 55, name: 'Coca Cola / Sprite 300ml', priceCents: 8000, costCents: 4500, color: '#dc2626', sku: 'BAR-010', stockQty: 60, unit: 'btl'),
        Product(id: 611, categoryId: 56, name: 'Salted Roasted Peanuts', priceCents: 10000, costCents: 5000, color: '#b45309', sku: 'BAR-011', stockQty: 40, unit: 'pkt'),
      ],
    };
  }
}
