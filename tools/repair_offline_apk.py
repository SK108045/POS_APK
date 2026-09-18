from pathlib import Path
import json, re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'capacitor/www/app.js'
CSS = ROOT / 'capacitor/www/styles.css'
INDEX = ROOT / 'capacitor/www/index.html'
PKG = ROOT / 'capacitor/package.json'
CONFIG = ROOT / 'capacitor/capacitor.config.json'
BUILD = ROOT / '.github/workflows/build-apk.yml'
GITIGNORE = ROOT / '.gitignore'
README = ROOT / 'README.md'

app = APP.read_text(encoding='utf-8')

localpos = r'''const CLOUD_API_BASE = (localStorage.getItem('pos_cloud_api_base') || 'http://3.87.19.244:5000').replace(/\/$/, '');
const CLOUD_ONLY_PATHS = [
  '/api/admin/sms/config',
  '/api/admin/sms/send',
  '/api/product/image-search',
  '/api/product/save-image'
];

const LocalPOS = {
  shopKey(name, btype = null) {
    const type = btype || localStorage.getItem('pos_active_business_type') || 'retail';
    return `shop:${type}:${name}`;
  },
  async get(key, fallback) {
    try {
      if (window.OraforgeDBReady) await window.OraforgeDBReady;
      if (window.OraforgeDB) return await window.OraforgeDB.get(key, fallback);
    } catch (e) {
      console.warn('Local DB read fallback:', e);
    }
    try {
      const raw = localStorage.getItem('fallback_' + key);
      return raw == null ? fallback : JSON.parse(raw);
    } catch (e) { return fallback; }
  },
  async set(key, value) {
    try {
      if (window.OraforgeDBReady) await window.OraforgeDBReady;
      if (window.OraforgeDB) {
        await window.OraforgeDB.set(key, value);
        return;
      }
    } catch (e) {
      console.warn('Local DB write fallback:', e);
    }
    localStorage.setItem('fallback_' + key, JSON.stringify(value));
  },
  async getShop(name, fallback, btype = null) {
    return this.get(this.shopKey(name, btype), fallback);
  },
  async setShop(name, value, btype = null) {
    return this.set(this.shopKey(name, btype), value);
  },
  async seedShop(btype, force = false) {
    const prof = LOCAL_PROFILES_DATA.profiles[btype] || LOCAL_PROFILES_DATA.profiles.retail;
    const sample = LOCAL_PROFILES_DATA.sample_data[btype] || LOCAL_PROFILES_DATA.sample_data.retail;
    const seeded = await this.getShop('seeded', false, btype);
    if (seeded && !force) return;

    const cats = sample.categories.map((name, i) => ({
      id: i + 1,
      name,
      sort_order: i,
      business_type: btype
    }));
    const items = sample.items.map((it, i) => ({
      id: i + 1,
      category_id: Math.max(1, sample.categories.indexOf(it.category) + 1),
      name: it.name,
      price_cents: Math.round(Number(it.price || 0) * 100),
      wholesale_price_cents: Math.round(Number(it.wholesale_price || 0) * 100),
      cost_cents: Math.round(Number(it.cost || 0) * 100),
      color: it.color || '#334155',
      sku: it.sku || `SKU-${i + 1}`,
      barcode: it.barcode || '',
      stock_qty: Number(it.stock_qty ?? it.stock ?? 0),
      unit: it.unit || 'pcs',
      reorder_level: Number(it.reorder_level ?? 5),
      batch_no: it.batch_no || '',
      expiry_date: it.expiry_date || '',
      manufacturer: it.manufacturer || '',
      strength: it.strength || '',
      variants_json: it.variants_json || '',
      decimal_qty_enabled: Number(it.decimal_qty_enabled || 0),
      image_url: it.image_url || '',
      active: 1
    }));

    await this.setShop('categories', cats, btype);
    await this.setShop('items', items, btype);
    if (force || !(await this.getShop('settings', null, btype))) {
      await this.setShop('settings', {
        business_name: prof.name + ' POS',
        business_tagline: prof.tagline || '',
        business_type: btype,
        tax_rate: 16.0,
        currency: 'KES',
        receipt_header: 'Welcome to ' + prof.name,
        receipt_footer: 'Thank you for your business!\n------- END OF RECEIPT -------'
      }, btype);
    }
    if (!(await this.getShop('orders', null, btype))) await this.setShop('orders', [], btype);
    if (!(await this.getShop('suppliers', null, btype))) {
      await this.setShop('suppliers', [
        { id: 1, name: 'Local Wholesale Distributor', phone: '', email: '', active: 1 }
      ], btype);
    }
    if (!(await this.getShop('customers', null, btype))) {
      await this.setShop('customers', [{ id: 1, name: 'Walk-In Customer', phone: '' }], btype);
    }
    await this.setShop('seeded', true, btype);
  },
  async switchProfile(btype) {
    const type = LOCAL_PROFILES_DATA.profiles[btype] ? btype : 'retail';
    localStorage.setItem('pos_active_business_type', type);
    await this.seedShop(type, false);
    return type;
  },
  async init() {
    const type = localStorage.getItem('pos_active_business_type') || 'retail';
    await this.seedShop(type, false);
    return type;
  },
  recalc(order) {
    order.subtotal_cents = (order.items || []).reduce((sum, it) => sum + Number(it.line_total_cents || 0), 0);
    order.tax_cents = 0;
    order.total_cents = order.subtotal_cents;
    order.updated_at = Math.floor(Date.now() / 1000);
    return order;
  },
  nextId(rows) {
    return (rows || []).reduce((m, row) => Math.max(m, Number(row.id || 0)), 0) + 1;
  },
  async saveOrders(orders, btype) {
    await this.setShop('orders', orders, btype);
  },
  async handle(path, options = {}) {
    const btype = await this.init();
    const url = new URL(path, 'https://local.pos');
    const cleanPath = url.pathname;
    const method = (options.method || 'GET').toUpperCase();
    const body = options.body ? (typeof options.body === 'string' ? JSON.parse(options.body) : options.body) : {};
    const prof = LOCAL_PROFILES_DATA.profiles[btype] || LOCAL_PROFILES_DATA.profiles.retail;

    if (cleanPath === '/api/bootstrap') {
      const cats = await this.getShop('categories', [], btype);
      const items = await this.getShop('items', [], btype);
      const settings = await this.getShop('settings', {}, btype);
      const low = items.filter(i => Number(i.stock_qty || 0) <= Number(i.reorder_level || 5)).length;
      return {
        user: { id: 1, username: 'terminal', full_name: 'POS Terminal', role: 'cashier', business_type: btype },
        settings,
        profile: prof,
        profiles: LOCAL_PROFILES_DATA.profiles,
        capabilities: prof.capabilities || {},
        employees: [{ id: 1, name: 'POS Terminal' }, { id: 2, name: 'The Owner' }],
        menu: { categories: cats, items },
        tables: [{ id: 1, name: 'Counter 1', seats: 4 }, { id: 2, name: 'Counter 2', seats: 4 }],
        alerts: { expiry: 0, low_stock: low }
      };
    }

    if (cleanPath === '/api/orders' && method === 'POST') {
      const orders = await this.getShop('orders', [], btype);
      const now = Math.floor(Date.now() / 1000);
      const order = {
        id: this.nextId(orders),
        ticket_no: `R${String(now).slice(-6)}-${String(orders.length + 1).padStart(3, '0')}`,
        business_type: btype,
        order_type: body.order_type || prof.order_type_default || 'walk-in',
        customer_name: body.customer_name || '',
        table_id: body.table_id || null,
        table_name: body.table_id ? `Counter ${body.table_id}` : '',
        employee_id: Number(body.employee_id || 1),
        employee_name: Number(body.employee_id || 1) === 2 ? 'The Owner' : 'POS Terminal',
        pricing_tier: body.pricing_tier || 'retail',
        is_quote: body.is_quote ? 1 : 0,
        notes: body.notes || '',
        status: 'open', subtotal_cents: 0, tax_cents: 0, total_cents: 0,
        paid_cents: 0, payment_method: '', payment_ref: '',
        created_at: now, updated_at: now, paid_at: null, items: []
      };
      orders.unshift(order);
      await this.saveOrders(orders, btype);
      return order;
    }

    if (cleanPath === '/api/order/add' && method === 'POST') {
      const orders = await this.getShop('orders', [], btype);
      const products = await this.getShop('items', [], btype);
      const order = orders.find(o => o.id === Number(body.order_id));
      const product = products.find(i => i.id === Number(body.menu_item_id));
      if (!order) throw new Error('Sale not found');
      if (!product) throw new Error('Product not found');
      const qty = Number(body.qty || 1);
      const price = body.pricing_tier === 'wholesale' && Number(product.wholesale_price_cents || 0) > 0
        ? Number(product.wholesale_price_cents)
        : Number(body.unit_price_cents || product.price_cents || 0);
      const variant = body.variant_info || '';
      const note = body.note || '';
      let row = (order.items || []).find(i => i.menu_item_id === product.id && (i.variant_info || '') === variant && (i.note || '') === note);
      if (row) {
        row.qty = Number(row.qty || 0) + qty;
        row.unit_price_cents = price;
        row.line_total_cents = Math.round(row.qty * price);
      } else {
        row = {
          id: this.nextId(order.items || []),
          menu_item_id: product.id,
          name: product.name,
          qty,
          unit_price_cents: price,
          line_total_cents: Math.round(qty * price),
          cost_cents: Number(product.cost_cents || 0),
          variant_info: variant,
          note,
          batch_no: body.batch_no || product.batch_no || ''
        };
        order.items.push(row);
      }
      this.recalc(order);
      await this.saveOrders(orders, btype);
      return order;
    }

    if (cleanPath === '/api/order/qty' && method === 'POST') {
      const orders = await this.getShop('orders', [], btype);
      let found = null;
      for (const order of orders) {
        const idx = (order.items || []).findIndex(i => i.id === Number(body.item_id));
        if (idx < 0) continue;
        if (Number(body.qty) <= 0) order.items.splice(idx, 1);
        else {
          const row = order.items[idx];
          row.qty = Number(body.qty);
          row.line_total_cents = Math.round(row.qty * Number(row.unit_price_cents || 0));
        }
        this.recalc(order);
        found = order;
        break;
      }
      if (!found) throw new Error('Cart item not found');
      await this.saveOrders(orders, btype);
      return found;
    }

    if (cleanPath === '/api/order/status' && method === 'POST') {
      const orders = await this.getShop('orders', [], btype);
      const order = orders.find(o => o.id === Number(body.order_id));
      if (!order) throw new Error('Sale not found');
      order.status = body.status || order.status;
      order.updated_at = Math.floor(Date.now() / 1000);
      await this.saveOrders(orders, btype);
      return order;
    }

    if (cleanPath === '/api/order/convert-quote' && method === 'POST') {
      const orders = await this.getShop('orders', [], btype);
      const order = orders.find(o => o.id === Number(body.order_id));
      if (!order) throw new Error('Quotation not found');
      order.is_quote = 0;
      order.status = 'open';
      order.order_type = 'walk-in';
      this.recalc(order);
      await this.saveOrders(orders, btype);
      return order;
    }

    if (cleanPath === '/api/order/pay' && method === 'POST') {
      const orders = await this.getShop('orders', [], btype);
      const products = await this.getShop('items', [], btype);
      const customers = await this.getShop('customers', [], btype);
      const order = orders.find(o => o.id === Number(body.order_id));
      if (!order) throw new Error('Sale not found');
      if (order.status !== 'paid') {
        for (const oi of order.items || []) {
          const product = products.find(p => p.id === oi.menu_item_id);
          if (product) product.stock_qty = Math.max(0, Number(product.stock_qty || 0) - Number(oi.qty || 0));
        }
      }
      order.status = 'paid';
      order.payment_method = body.payment_method || 'cash';
      order.payment_ref = body.payment_ref || (order.payment_method === 'cash' ? 'CASH' : `TXN-${Date.now()}`);
      order.paid_cents = order.total_cents;
      order.paid_at = Math.floor(Date.now() / 1000);
      order.updated_at = order.paid_at;
      const phone = String(body.customer_phone || '').trim();
      if (phone && !customers.some(c => String(c.phone || '').replace(/\D/g, '') === phone.replace(/\D/g, ''))) {
        customers.push({ id: this.nextId(customers), name: order.customer_name || phone, phone, email: '', notes: '' });
      }
      await this.saveOrders(orders, btype);
      await this.setShop('items', products, btype);
      await this.setShop('customers', customers, btype);
      return order;
    }

    if (cleanPath === '/api/orders' && method === 'GET') {
      const orders = await this.getShop('orders', [], btype);
      const status = url.searchParams.get('status');
      return status ? orders.filter(o => o.status === status) : orders;
    }

    if (cleanPath === '/api/order' && method === 'GET') {
      const orders = await this.getShop('orders', [], btype);
      return orders.find(o => o.id === Number(url.searchParams.get('id'))) || {};
    }

    if (cleanPath === '/api/payments') {
      const q = (url.searchParams.get('q') || '').toLowerCase();
      const orders = (await this.getShop('orders', [], btype)).filter(o => o.status === 'open' || o.status === 'sent');
      return q ? orders.filter(o => `${o.ticket_no} ${o.customer_name} ${o.employee_name}`.toLowerCase().includes(q)) : orders;
    }

    if (cleanPath === '/api/suppliers') return await this.getShop('suppliers', [], btype);
    if (cleanPath === '/api/customers') return await this.getShop('customers', [], btype);

    if (cleanPath === '/api/admin/supplier' && method === 'POST') {
      const suppliers = await this.getShop('suppliers', [], btype);
      let supplier = body.id ? suppliers.find(s => s.id === Number(body.id)) : null;
      if (!supplier) {
        supplier = { id: this.nextId(suppliers) };
        suppliers.push(supplier);
      }
      Object.assign(supplier, { name: body.name || supplier.name || 'Supplier', phone: body.phone || '', email: body.email || '', active: Number(body.active ?? 1) });
      await this.setShop('suppliers', suppliers, btype);
      return supplier;
    }

    if (cleanPath === '/api/supplier/detail') {
      const suppliers = await this.getShop('suppliers', [], btype);
      const products = await this.getShop('items', [], btype);
      const supplier = suppliers.find(s => s.id === Number(url.searchParams.get('id')));
      if (!supplier) throw new Error('Supplier not found');
      return { ...supplier, total_purchases: 0, products: products.filter(p => Number(p.supplier_id || 0) === supplier.id) };
    }

    if (cleanPath === '/api/settings' && method === 'POST') {
      const current = await this.getShop('settings', {}, btype);
      const settings = { ...current, ...body, business_type: btype };
      await this.setShop('settings', settings, btype);
      return { settings, profile: prof, capabilities: prof.capabilities || {} };
    }

    if (cleanPath === '/api/seed-samples' && method === 'POST') {
      await this.seedShop(btype, true);
      return { ok: true, menu: { categories: await this.getShop('categories', [], btype), items: await this.getShop('items', [], btype) } };
    }

    if (cleanPath === '/api/menu/item' && method === 'POST') {
      const categories = await this.getShop('categories', [], btype);
      const items = await this.getShop('items', [], btype);
      let item = body.id ? items.find(i => i.id === Number(body.id)) : null;
      if (!item) {
        item = { id: this.nextId(items), active: 1 };
        items.push(item);
      }
      Object.assign(item, {
        category_id: Number(body.category_id || item.category_id || 1),
        name: body.name || item.name || 'Product',
        sku: body.sku || '', barcode: body.barcode || '', unit: body.unit || 'pcs',
        stock_qty: Number(body.stock_qty ?? item.stock_qty ?? 0),
        reorder_level: Number(body.reorder_level ?? item.reorder_level ?? 5),
        cost_cents: Math.round(Number(body.cost || 0) * 100),
        price_cents: Math.round(Number(body.price || 0) * 100),
        wholesale_price_cents: Math.round(Number(body.wholesale_price || 0) * 100),
        batch_no: body.batch_no || '', expiry_date: body.expiry_date || '',
        manufacturer: body.manufacturer || '', strength: body.strength || '',
        variants_json: body.variants_json || '', decimal_qty_enabled: body.decimal_qty_enabled ? 1 : 0,
        image_url: body.image_base64 || body.image_url || item.image_url || '', color: body.color || item.color || '#334155'
      });
      await this.setShop('items', items, btype);
      return { categories, items };
    }

    if (cleanPath === '/api/menu/item' && method === 'DELETE') {
      const id = Number(url.searchParams.get('id'));
      const orders = await this.getShop('orders', [], btype);
      if (orders.some(o => (o.items || []).some(i => i.menu_item_id === id))) return { error: 'Cannot delete product with sales history.' };
      const categories = await this.getShop('categories', [], btype);
      const items = (await this.getShop('items', [], btype)).filter(i => i.id !== id);
      await this.setShop('items', items, btype);
      return { categories, items };
    }

    if (cleanPath === '/api/stock') return await this.getShop('items', [], btype);
    if (cleanPath === '/api/stock/adjust' && method === 'POST') {
      const items = await this.getShop('items', [], btype);
      const item = items.find(i => i.id === Number(body.product_id));
      if (!item) throw new Error('Product not found');
      item.stock_qty = Math.max(0, Number(item.stock_qty || 0) + Number(body.qty_change || 0));
      await this.setShop('items', items, btype);
      return { ok: true, item };
    }

    if (cleanPath === '/api/reports') {
      const period = url.searchParams.get('period') || 'today';
      const now = new Date();
      let start = new Date(now);
      if (period === 'yesterday') { start.setDate(start.getDate() - 1); start.setHours(0,0,0,0); }
      else if (period === 'week') { start.setDate(start.getDate() - 6); start.setHours(0,0,0,0); }
      else if (period === 'month') { start.setDate(start.getDate() - 29); start.setHours(0,0,0,0); }
      else start.setHours(0,0,0,0);
      let end = now;
      if (period === 'yesterday') { end = new Date(start); end.setDate(end.getDate() + 1); }
      const startTs = Math.floor(start.getTime()/1000), endTs = Math.floor(end.getTime()/1000) + 1;
      const orders = (await this.getShop('orders', [], btype)).filter(o => o.status === 'paid' && Number(o.paid_at || o.updated_at || 0) >= startTs && Number(o.paid_at || o.updated_at || 0) < endTs);
      const products = await this.getShop('items', [], btype);
      let sales = 0, costs = 0;
      const paymentMap = new Map(), top = new Map();
      for (const o of orders) {
        sales += Number(o.total_cents || 0);
        const pm = o.payment_method || 'cash';
        paymentMap.set(pm, (paymentMap.get(pm) || 0) + Number(o.total_cents || 0));
        for (const it of o.items || []) {
          costs += Number(it.cost_cents || 0) * Number(it.qty || 0);
          const cur = top.get(it.menu_item_id) || { name: it.name, qty: 0, sales: 0, current_stock: 0 };
          cur.qty += Number(it.qty || 0); cur.sales += Number(it.line_total_cents || 0);
          cur.current_stock = Number(products.find(p => p.id === it.menu_item_id)?.stock_qty || 0);
          top.set(it.menu_item_id, cur);
        }
      }
      const inventoryValue = products.reduce((s,p) => s + Number(p.stock_qty || 0) * Number(p.cost_cents || 0), 0);
      const potentialProfit = products.reduce((s,p) => s + Number(p.stock_qty || 0) * Math.max(0, Number(p.price_cents || 0) - Number(p.cost_cents || 0)), 0);
      return {
        totals: { sales, costs, orders: orders.length },
        payments: [...paymentMap.entries()].map(([method, amount]) => ({ method, amount, transactions: orders.filter(o => (o.payment_method || 'cash') === method).length })),
        top_items: [...top.values()].sort((a,b) => b.sales - a.sales).slice(0, 15),
        stock: { inventory_value: inventoryValue, potential_profit: potentialProfit },
        period,
        range: { start: startTs, end: endTs, label: period === 'today' ? 'Today' : period === 'yesterday' ? 'Yesterday' : period === 'week' ? 'Last 7 days' : 'Last 30 days' }
      };
    }

    throw new Error(`Offline feature not implemented yet: ${cleanPath}`);
  }
};

async function api(path, options = {}) {
  const cloudOnly = CLOUD_ONLY_PATHS.some(prefix => path.startsWith(prefix));
  if (cloudOnly) {
    if (!navigator.onLine) throw new Error('This feature needs an internet connection.');
    const init = { headers: { 'Content-Type': 'application/json' }, credentials: 'include', ...options };
    if (init.body && typeof init.body !== 'string') init.body = JSON.stringify(init.body);
    const res = await fetch(CLOUD_API_BASE + path, init);
    let payload = {};
    try { payload = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error(payload.error || payload.message || `Online service failed (${res.status})`);
    return payload;
  }
  return LocalPOS.handle(path, options);
}
'''

pattern = re.compile(r"const LocalPOS = \{.*?\n\};\n\nasync function api\(path, options = \{\}\) \{.*?\n\}\n", re.S)
if not pattern.search(app):
    raise SystemExit('Could not find LocalPOS/api block')
app = pattern.sub(localpos + '\n', app, count=1)

pos_layout = r'''function posLayout() {
  const root = qs('[data-page="pos"]');
  document.body.classList.remove('mobile-cart-open');
  const itemLabel = state.profile?.item_label || 'Products';
  const orderTypes = (state.profile?.order_types && state.profile.order_types.length)
    ? state.profile.order_types
    : ['walk-in', 'quote', 'layaway'];

  root.innerHTML = `
    <div class="mobile-cart-backdrop" id="mobileCartBackdrop" aria-hidden="true"></div>
    <section class="menu-side">
      <div class="pos-head mobile-pos-head">
        <div class="pos-title-block">
          <span class="pos-kicker">Quick sale</span>
          <h2>${itemLabel}</h2>
          <small>Tap a product to add it instantly</small>
        </div>
        <div class="pos-control-strip">
          ${hasCap('wholesale_pricing') ? `<button type="button" id="tierToggleBtn" class="tier-toggle-btn ${state.pricingTier === 'wholesale' ? 'active' : ''}">${state.pricingTier === 'wholesale' ? '⚡ Wholesale' : '🏷️ Retail'}</button>` : ''}
          ${hasCap('tables') ? `<select id="tableSelect" class="field"><option value="">Table / Tab</option>${state.tables.map(t => `<option value="${t.id}" ${state.selectedTableId == t.id ? 'selected' : ''}>${t.name}</option>`).join('')}</select>` : ''}
          ${hasCap('waiters') ? `<select id="waiterSelect" class="field"><option value="">Staff / Waiter</option>${state.employees.map(e => `<option value="${e.id}" ${state.selectedEmployeeId == e.id ? 'selected' : ''}>${e.name}</option>`).join('')}</select>` : ''}
          <select id="orderType" class="field">${orderTypes.map(t => `<option value="${t}">${t.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>`).join('')}</select>
        </div>
      </div>
      <div class="sku-search-wrap mobile-search-row">
        <div class="sku-search-inner">
          <span class="sku-search-icon">&#128269;</span>
          <input class="sku-search-input" id="skuSearch" placeholder="${hasCap('barcode') ? 'Search name, SKU or scan barcode…' : 'Search by name or SKU…'}" autocomplete="off" autocorrect="off">
          <button class="sku-search-clear" id="skuClear" title="Clear">&#215;</button>
        </div>
        <button type="button" class="barcode-scan-btn" id="posBarcodeScanBtn" title="Scan Barcode"><span class="barcode-glyph">▥</span><span>Scan</span></button>
      </div>
      <div class="tabs" id="catTabs"></div>
      <div class="item-grid" id="itemGrid"></div>
    </section>
    <aside class="ticket-side mobile-ticket-drawer" id="mobileTicketDrawer">
      <div class="ticket-head">
        <div><h2>${hasCap('tables') ? 'Ticket / Tab' : 'Sale'}</h2><small>${state.profile?.name || 'POS'}</small></div>
        <div class="ticket-staff">${selectedEmployeeName() || state.user?.username || 'Staff'}</div>
        <button type="button" class="mobile-cart-close" id="mobileCartClose" aria-label="Close cart">×</button>
      </div>
      <div class="ticket-list" id="ticketList"></div>
      <div class="ticket-foot" id="ticketFoot"></div>
    </aside>
    <div class="mobile-cart-bar">
      <button type="button" class="mobile-cart-summary" id="mobileCartBar" aria-label="Open sale cart">
        <span class="mobile-cart-items"><span class="mobile-cart-icon">🛒</span><strong id="mobileCartCount">0</strong><span>items</span></span>
        <strong class="mobile-cart-total" id="mobileCartTotal">KES 0.00</strong>
        <span class="mobile-cart-action">View cart ↑</span>
      </button>
    </div>`;

  qs('#orderType')?.addEventListener('change', ensureOrder);
  qs('#tableSelect')?.addEventListener('change', e => {
    state.selectedTableId = e.target.value ? Number(e.target.value) : null;
    if (state.order) { state.order.table_id = state.selectedTableId; state.order.table_name = state.tables.find(t => t.id === state.selectedTableId)?.name || ''; renderTicket(); }
  });
  qs('#waiterSelect')?.addEventListener('change', e => {
    state.selectedEmployeeId = e.target.value ? Number(e.target.value) : null;
    if (state.order) { state.order.employee_id = state.selectedEmployeeId; state.order.employee_name = selectedEmployeeName(); renderTicket(); }
  });
  qs('#tierToggleBtn')?.addEventListener('click', () => {
    state.pricingTier = state.pricingTier === 'wholesale' ? 'retail' : 'wholesale';
    qs('#tierToggleBtn').classList.toggle('active', state.pricingTier === 'wholesale');
    qs('#tierToggleBtn').textContent = state.pricingTier === 'wholesale' ? '⚡ Wholesale' : '🏷️ Retail';
    renderItems();
  });
  qs('#posBarcodeScanBtn')?.addEventListener('click', () => showBarcodeModal('pos'));
  qs('#mobileCartBar')?.addEventListener('click', () => setMobileCartOpen(true));
  qs('#mobileCartBackdrop')?.addEventListener('click', () => setMobileCartOpen(false));
  qs('#mobileCartClose')?.addEventListener('click', () => setMobileCartOpen(false));

  const skuInput = qs('#skuSearch');
  skuInput.addEventListener('input', () => { state.searchQuery = skuInput.value.trim().toLowerCase(); renderItems(); });
  qs('#skuClear').addEventListener('click', () => { skuInput.value = ''; state.searchQuery = ''; renderItems(); skuInput.focus(); });
  skuInput.addEventListener('keydown', async e => {
    if (e.key !== 'Enter') return;
    const q = skuInput.value.trim().toLowerCase();
    if (!q) return;
    const match = (state.items || []).find(i => (i.barcode && i.barcode.trim().toLowerCase() === q) || (i.sku && i.sku.trim().toLowerCase() === q));
    if (!match) { playBeep('error'); toast(`Barcode / SKU "${skuInput.value.trim()}" not found`, 'error'); return; }
    if (hasCap('variants') && match.variants_json) showVariantModal(match);
    else await addItemWithQty(match.id, 1);
    playBeep('success'); skuInput.value = ''; state.searchQuery = ''; renderItems();
  });
  renderTabs(); renderItems(); renderTicket(); updateMobileCartBar();
}
'''

pos_pat = re.compile(r"function posLayout\(\) \{.*?\n\}\n\nfunction getCategoryIcon", re.S)
if not pos_pat.search(app):
    raise SystemExit('Could not find posLayout block')
app = pos_pat.sub(pos_layout + '\nfunction getCategoryIcon', app, count=1)

helpers = r'''function setMobileCartOpen(open) {
  document.body.classList.toggle('mobile-cart-open', Boolean(open));
}

function updateMobileCartBar() {
  const bar = qs('#mobileCartBar');
  const countEl = qs('#mobileCartCount');
  const totalEl = qs('#mobileCartTotal');
  if (!bar || !countEl || !totalEl) return;
  const items = state.order?.items || [];
  const quantity = items.reduce((sum, item) => sum + Number(item.qty || 0), 0);
  countEl.textContent = Number.isInteger(quantity) ? String(quantity) : quantity.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
  totalEl.textContent = money(state.order?.total_cents || 0);
  bar.classList.toggle('has-items', quantity > 0);
}

'''
if 'function setMobileCartOpen(' not in app:
    app = app.replace('function renderTicket() {', helpers + 'function renderTicket() {', 1)
app = app.replace("  if (!list || !foot) return;\n\n  if (!state.order) {", "  if (!list || !foot) return;\n  updateMobileCartBar();\n\n  if (!state.order) {", 1)
app = app.replace('    LocalPOS.switchProfile(selectedShop);', '    await LocalPOS.switchProfile(selectedShop);')

# Remove in-portal profile cards and switching on APK settings page.
app = app.replace("  const profilesList = Object.entries(state.profiles || {});\n", '')
shop_section = re.compile(r"\n\s*<!-- ── Shop Category Selector.*?\n\s*<form id=\"settingsForm\"", re.S)
app = shop_section.sub('\n\n      <form id="settingsForm"', app, count=1)
handler = re.compile(r"\n\s*// 1-Click Profile switch handler.*?\n\s*// Sample catalog loader", re.S)
app = handler.sub('\n\n  // Sample catalog loader', app, count=1)
app = app.replace('Business Settings & Profiles', 'Business Settings')
app = app.replace('Select your shop category and appearance preferences below. Each business profile enables tailored features (tables, barcodes, expiry dates, variants, quotes) and loads its dedicated product catalog without deleting your existing sales.', 'Manage this shop\'s appearance, receipt and business details. The shop category is selected only when you log in.')
APP.write_text(app, encoding='utf-8')

css = CSS.read_text(encoding='utf-8')
marker = '/* ── ORAFORGE MOBILE APK POS ── */'
if marker not in css:
    css += r'''

/* ── ORAFORGE MOBILE APK POS ── */
.mobile-cart-backdrop,.mobile-cart-bar,.mobile-cart-close{display:none}
.pos-title-block{display:flex;flex-direction:column;gap:1px}.pos-kicker{font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}.pos-title-block small{font-size:12px;color:var(--muted)}
.pos-control-strip{display:flex;align-items:center;gap:8px;margin-left:auto;flex-wrap:wrap}.pos-control-strip .field{width:auto;min-width:110px;padding:7px 10px;font-size:13px}
.mobile-search-row{display:flex;gap:8px;align-items:center}.mobile-search-row .sku-search-inner{flex:1}
@media (max-width:700px){
  html,body{width:100%;max-width:100%;overflow-x:hidden} body{padding:0!important} main{width:100%;max-width:100vw;overflow-x:hidden}
  .topbar{height:58px!important;width:100%!important;padding:0 10px!important;grid-template-columns:minmax(0,1fr) auto!important;gap:6px!important;position:sticky;top:0;z-index:5000}
  .topbar-left{min-width:0;overflow:hidden}.brand{min-width:0;gap:7px}.brand-logo{width:34px;height:34px;flex:0 0 34px}.brand-text{min-width:0}.brand-text span{font-size:13px!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}.brand-text small{display:none}.topbar-divider{display:none}
  .topbar-right{gap:5px}.topbar-clock #navDate{display:none}.topbar-clock #navTime{font-size:12px!important}.theme-toggle-btn{width:36px!important;height:36px!important}.logout{font-size:0!important;width:36px;height:36px;padding:0!important;display:grid;place-items:center}.logout::before{content:'↪';font-size:18px}
  .pos-shell{display:block!important;width:100%!important;max-width:100vw!important;height:auto!important;min-height:calc(100dvh - 58px)!important;margin:0!important;padding:0 0 78px!important;overflow:visible!important;background:var(--bg)!important}
  .menu-side{width:100%!important;max-width:100%!important;border:0!important;border-radius:0!important;box-shadow:none!important;display:block!important;overflow:visible!important}
  .mobile-pos-head{display:flex!important;align-items:center!important;padding:10px 12px 8px!important;border-bottom:1px solid var(--line)!important;gap:8px!important}.pos-title-block{min-width:0;flex:1}.pos-title-block h2{font-size:18px!important}.pos-title-block small{display:none}.pos-kicker{font-size:9px}
  .pos-control-strip{margin-left:0!important;flex:0 0 auto!important;max-width:44%!important}.pos-control-strip .field{min-width:0!important;width:auto!important;max-width:120px!important;height:38px!important;padding:7px 8px!important;font-size:12px!important}.pos-control-strip #tierToggleBtn{max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .sku-search-wrap.mobile-search-row{padding:8px 10px!important;gap:7px!important;background:var(--panel)!important}.sku-search-inner{min-width:0!important}.sku-search-input{font-size:13px!important;padding:10px 0!important}.barcode-scan-btn{height:42px!important;padding:0 12px!important;font-size:12px!important;border-radius:9px!important}.barcode-glyph{font-size:18px}
  .tabs{padding:7px 10px!important;gap:7px!important;overflow-x:auto!important;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}.tab{flex:0 0 auto!important;white-space:nowrap!important;min-height:38px!important;padding:8px 12px!important;font-size:11px!important}
  .item-grid{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:10px!important;padding:10px!important;overflow:visible!important;height:auto!important;max-height:none!important;background:var(--bg)!important}
  .menu-btn{min-width:0!important;min-height:212px!important;height:auto!important;border-radius:13px!important;overflow:hidden!important;text-align:left!important}.menu-btn-img-wrapper{height:116px!important;min-height:116px!important}.menu-btn-img-wrapper img{padding:8px!important}.menu-btn-content{padding:10px!important;gap:4px!important}.menu-btn-content strong{font-size:13px!important;line-height:1.25!important;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.item-sku{font-size:10px!important}.item-price{font-size:14px!important}.stock-badge{top:7px!important;right:7px!important;font-size:9px!important;padding:3px 6px!important}.menu-btn-stock-status{font-size:10px!important;width:max-content!important;padding:3px 7px!important;border-radius:999px!important}
  .mobile-cart-bar{display:block!important;position:fixed;left:0;right:0;bottom:0;padding:8px 10px calc(8px + env(safe-area-inset-bottom));z-index:6500;background:linear-gradient(to top,var(--bg) 68%,transparent)}
  .mobile-cart-summary{width:100%;min-height:56px;border:1px solid var(--line);border-radius:14px;background:var(--panel);color:var(--ink);box-shadow:0 8px 30px rgba(0,0,0,.18);display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 14px;gap:8px}.mobile-cart-items{display:flex;align-items:center;gap:5px;font-size:12px}.mobile-cart-total{font-size:15px}.mobile-cart-action{text-align:right;font-size:10px;font-weight:800}.mobile-cart-summary.has-items{border-color:var(--ink)}
  .mobile-ticket-drawer{display:grid!important;position:fixed!important;left:0!important;right:0!important;bottom:0!important;top:auto!important;width:100%!important;max-width:none!important;height:min(86dvh,720px)!important;min-height:0!important;border-radius:20px 20px 0 0!important;z-index:8000!important;transform:translateY(105%)!important;transition:transform .22s ease!important;box-shadow:0 -18px 60px rgba(0,0,0,.32)!important;background:var(--panel)!important;padding-bottom:env(safe-area-inset-bottom)}
  body.mobile-cart-open .mobile-ticket-drawer{transform:translateY(0)!important} body.mobile-cart-open{overflow:hidden}.mobile-cart-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.52);z-index:7900}.mobile-cart-open .mobile-cart-backdrop{display:block}.mobile-cart-close{display:grid!important;place-items:center;width:36px;height:36px;border:0;border-radius:50%;background:var(--bg);color:var(--ink);font-size:24px}.ticket-head{grid-template-columns:1fr auto auto!important}.ticket-staff{font-size:12px!important}.ticket-list{overflow:auto!important}.ticket-foot{max-height:46dvh;overflow:auto}
  .qty-popup-overlay,.modal-overlay{padding:0!important;align-items:flex-end!important}.qty-popup,.modal-box{width:100%!important;max-width:none!important;border-radius:20px 20px 0 0!important;max-height:92dvh!important;padding-bottom:calc(20px + env(safe-area-inset-bottom))!important}
}
@media (max-width:390px){.item-grid{gap:8px!important;padding:8px!important}.menu-btn{min-height:196px!important}.menu-btn-img-wrapper{height:102px!important;min-height:102px!important}.mobile-cart-total{font-size:14px}.pos-control-strip{max-width:42%!important}}
'''
CSS.write_text(css, encoding='utf-8')

bridge = r'''import { Capacitor } from '@capacitor/core';
import { CapacitorSQLite, SQLiteConnection } from '@capacitor-community/sqlite';

class IndexedFallback {
  constructor(){ this.dbp = null; }
  open(){
    if (this.dbp) return this.dbp;
    this.dbp = new Promise((resolve,reject)=>{
      const req=indexedDB.open('oraforge_pos_fallback',1);
      req.onupgradeneeded=()=>{ const db=req.result; if(!db.objectStoreNames.contains('kv')) db.createObjectStore('kv'); };
      req.onsuccess=()=>resolve(req.result); req.onerror=()=>reject(req.error);
    });
    return this.dbp;
  }
  async get(key,fallback){ const db=await this.open(); return new Promise((resolve,reject)=>{ const tx=db.transaction('kv','readonly'); const r=tx.objectStore('kv').get(key); r.onsuccess=()=>resolve(r.result===undefined?fallback:r.result); r.onerror=()=>reject(r.error); }); }
  async set(key,value){ const db=await this.open(); return new Promise((resolve,reject)=>{ const tx=db.transaction('kv','readwrite'); tx.objectStore('kv').put(value,key); tx.oncomplete=()=>resolve(); tx.onerror=()=>reject(tx.error); }); }
}

class OraforgeDB {
  constructor(){ this.sqlite=null; this.db=null; this.fallback=new IndexedFallback(); this.native=false; }
  async init(){
    this.native = ['android','ios'].includes(Capacitor.getPlatform());
    if (!this.native) return this;
    try {
      this.sqlite = new SQLiteConnection(CapacitorSQLite);
      try { this.db = await this.sqlite.createConnection('oraforge_pos', false, 'no-encryption', 1, false); }
      catch (_) { this.db = await this.sqlite.retrieveConnection('oraforge_pos', false); }
      await this.db.open();
      await this.db.execute('CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL);');
    } catch (err) {
      console.error('Native SQLite unavailable; using IndexedDB fallback', err);
      this.native = false; this.db = null;
    }
    return this;
  }
  async get(key,fallback){
    if (!this.native || !this.db) return this.fallback.get(key,fallback);
    const r = await this.db.query('SELECT value FROM kv_store WHERE key = ? LIMIT 1;', [key]);
    if (!r.values || !r.values.length) return fallback;
    try { return JSON.parse(r.values[0].value); } catch (_) { return fallback; }
  }
  async set(key,value){
    if (!this.native || !this.db) return this.fallback.set(key,value);
    await this.db.run('INSERT OR REPLACE INTO kv_store(key,value) VALUES (?,?);', [key, JSON.stringify(value)]);
  }
}

window.OraforgeDB = new OraforgeDB();
window.OraforgeDBReady = window.OraforgeDB.init();
'''
(ROOT / 'capacitor/src').mkdir(parents=True, exist_ok=True)
(ROOT / 'capacitor/src/sqlite-bridge.js').write_text(bridge, encoding='utf-8')

index = INDEX.read_text(encoding='utf-8')
if 'sqlite-bridge.js' not in index:
    index = index.replace('  <script src="app.js" defer></script>', '  <script src="sqlite-bridge.js"></script>\n  <script src="app.js" defer></script>')
INDEX.write_text(index, encoding='utf-8')

pkg = json.loads(PKG.read_text(encoding='utf-8'))
pkg.setdefault('scripts', {})['build:bridge'] = 'esbuild src/sqlite-bridge.js --bundle --format=iife --platform=browser --outfile=www/sqlite-bridge.js'
pkg.setdefault('dependencies', {})['@capacitor-community/sqlite'] = '^6.0.0'
pkg.setdefault('devDependencies', {})['esbuild'] = '^0.25.0'
PKG.write_text(json.dumps(pkg, indent=2) + '\n', encoding='utf-8')

config = json.loads(CONFIG.read_text(encoding='utf-8'))
config['server'] = {'cleartext': True, 'androidScheme': 'https'}
CONFIG.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')

build = BUILD.read_text(encoding='utf-8')
build = build.replace('run: npm ci', 'run: npm install')
if 'Build SQLite bridge' not in build:
    build = build.replace('      - name: Add Android platform\n', '      - name: Build SQLite bridge\n        working-directory: capacitor\n        run: npm run build:bridge\n\n      - name: Add Android platform\n')
if 'Ensure Android network and camera permissions' not in build:
    build = build.replace('      - name: Build debug APK\n', '''      - name: Ensure Android network and camera permissions\n        working-directory: capacitor/android\n        run: |\n          python3 - <<'PY'\n          from pathlib import Path\n          p=Path('app/src/main/AndroidManifest.xml')\n          s=p.read_text()\n          for perm in ['android.permission.INTERNET','android.permission.CAMERA']:\n              line=f'<uses-permission android:name="{perm}" />'\n              if line not in s:\n                  s=s.replace('<application', line+'\\n    <application',1)\n          if 'android:usesCleartextTraffic=' not in s:\n              s=s.replace('<application', '<application android:usesCleartextTraffic="true"',1)\n          p.write_text(s)\n          PY\n\n      - name: Build debug APK\n''')
BUILD.write_text(build, encoding='utf-8')

ignore = GITIGNORE.read_text(encoding='utf-8') if GITIGNORE.exists() else ''
for entry in ['api.txt', 'capacitor/www/sqlite-bridge.js']:
    if entry not in ignore.splitlines(): ignore += ('\n' if ignore and not ignore.endswith('\n') else '') + entry + '\n'
GITIGNORE.write_text(ignore, encoding='utf-8')

secret = ROOT / 'api.txt'
if secret.exists(): secret.unlink()

readme = README.read_text(encoding='utf-8')
if '## Android APK architecture' not in readme:
    readme += '''\n\n## Android APK architecture\n\nThe Android build is offline-first. The Capacitor WebView bundles the POS UI locally and stores operational data on-device using native SQLite (`@capacitor-community/sqlite`) with an IndexedDB fallback for browser testing. Core sales do not require a Python server or internet connection. Network-only integrations such as SMS, cloud sync, remote image search and future M-Pesa integrations should call a remote HTTPS backend so API secrets are never bundled in the APK.\n'''
README.write_text(readme, encoding='utf-8')

# Basic validation
for required in ['/api/order/add', '/api/order/qty', '/api/order/pay', 'mobile-cart-bar', 'OraforgeDBReady']:
    if required not in APP.read_text(encoding='utf-8') and required not in CSS.read_text(encoding='utf-8'):
        raise SystemExit('Missing expected repair marker: ' + required)
print('Offline APK repair applied.')
