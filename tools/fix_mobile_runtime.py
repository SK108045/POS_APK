from pathlib import Path
import re

# 1) Native SQLite + native HTTP bridge
bridge_path = Path('capacitor/src/sqlite-bridge.js')
bridge = bridge_path.read_text()
bridge = bridge.replace("import { Capacitor } from '@capacitor/core';", "import { Capacitor, CapacitorHttp } from '@capacitor/core';")
if 'window.OraforgeHttp' not in bridge:
    bridge += r'''

window.OraforgeHttp = {
  async request({ url, method = 'GET', headers = {}, data = null, params = null, connectTimeout = 10000, readTimeout = 15000 }) {
    const options = { url, method, headers, connectTimeout, readTimeout };
    if (data !== null && data !== undefined) options.data = data;
    if (params) options.params = params;
    const response = await CapacitorHttp.request(options);
    if (response.status < 200 || response.status >= 300) {
      let message = `Network request failed (${response.status})`;
      const payload = response.data;
      if (payload && typeof payload === 'object') message = payload.error || payload.message || message;
      else if (typeof payload === 'string' && payload.trim()) message = payload.slice(0, 180);
      const error = new Error(message);
      error.status = response.status;
      error.data = payload;
      throw error;
    }
    return response;
  }
};
'''
bridge_path.write_text(bridge)

# 2) POS image search: direct public internet search, no Python session required
app_path = Path('capacitor/www/app.js')
app = app_path.read_text()
helper = r'''
async function searchOnlineProductImages(query, limit = 6) {
  const q = String(query || '').trim();
  if (!q) return { images: [], results: [] };
  if (!navigator.onLine) throw new Error('Image search needs an internet connection.');

  const url = `https://api.openverse.org/v1/images/?q=${encodeURIComponent(q)}&page_size=${Math.max(1, Math.min(limit, 12))}`;
  let payload;
  if (window.OraforgeHttp?.request) {
    const response = await window.OraforgeHttp.request({
      url,
      method: 'GET',
      headers: { Accept: 'application/json' }
    });
    payload = response.data;
    if (typeof payload === 'string') payload = JSON.parse(payload);
  } else {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`Image search failed (${response.status})`);
    payload = await response.json();
  }

  const images = (payload?.results || []).map(item => {
    const thumb = item.thumbnail || item.url;
    const full = item.url || thumb;
    return {
      thumb,
      thumbnail: thumb,
      full,
      url: full,
      title: item.title || q,
      source: 'Openverse'
    };
  }).filter(item => item.thumb && item.full);
  return { query: q, images, results: images };
}

'''
if 'async function searchOnlineProductImages' not in app:
    app = app.replace('// ── Online Image Search Modal ────────────────────────────────────────────────\nfunction showImageSearchModal', '// ── Online Image Search Modal ────────────────────────────────────────────────\n' + helper + 'function showImageSearchModal')
app = app.replace("const data = await api(`/api/product/image-search?q=${encodeURIComponent(q)}&limit=1`);", "const data = await searchOnlineProductImages(q, 6);")
app = app.replace('Finds the single best matching product photo online. Click <strong>Use This Image</strong> to download and optimize it locally with Pillow.', 'Searches Openverse directly from the phone. Select an image to use its online URL for this product.')
old_select = r'''      resultsBox.querySelector('#useThisImgBtn')?.addEventListener('click', async () => {
        const btn = resultsBox.querySelector('#useThisImgBtn');
        btn.disabled = true;
        btn.textContent = 'Optimizing and saving with Pillow...';
        statusEl.innerHTML = `<span style="color:var(--primary); font-weight:700;">Processing with Pillow...</span>`;

        try {
          const saved = await api('/api/product/save-image', {
            method: 'POST',
            body: { image_url: imgUrl, name: q }
          });
          if (saved.local_url) {
            onSelect(saved.local_url);
            toast('Image saved & optimized!', 'success');
            close();
          } else {
            throw new Error('Image save failed');
          }
        } catch(err) {
          statusEl.innerHTML = `<span style="color:var(--danger); font-weight:700;">Failed to download: ${err.message}</span>`;
          btn.disabled = false;
          btn.textContent = '✓ Use This Image';
        }
      });'''
new_select = r'''      resultsBox.querySelector('#useThisImgBtn')?.addEventListener('click', () => {
        onSelect(imgUrl);
        toast('Online product image selected!', 'success');
        close();
      });'''
if old_select not in app:
    raise SystemExit('Could not find image select block in app.js')
app = app.replace(old_select, new_select)
app_path.write_text(app)

# 3) Kill horizontal scrolling on the POS login and make shop chips genuinely fluid
styles_path = Path('capacitor/www/styles.css')
styles = styles_path.read_text()
login_css = r'''

/* ── APK login viewport hardening ───────────────────────────────────────── */
html, body { max-width: 100%; overflow-x: hidden; }
#posLoginScreen {
  box-sizing: border-box !important;
  width: 100vw !important;
  max-width: 100vw !important;
  overflow-x: hidden !important;
}
#posLoginScreen .login-panel {
  box-sizing: border-box !important;
  width: min(440px, 100%) !important;
  max-width: 100% !important;
  min-width: 0 !important;
}
#loginChipsContainer {
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  min-width: 0 !important;
  width: 100% !important;
}
#loginChipsContainer .login-shop-chip {
  box-sizing: border-box !important;
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
}
#loginChipsContainer .login-shop-chip > span:last-child {
  min-width: 0 !important;
  white-space: normal !important;
  overflow-wrap: anywhere !important;
}
@media (max-width: 380px) {
  #posLoginScreen { padding: 10px !important; }
  #posLoginScreen .login-panel { padding: 16px !important; }
  #loginChipsContainer { grid-template-columns: 1fr !important; }
}
'''
if 'APK login viewport hardening' not in styles:
    styles += login_css
styles_path.write_text(styles)

# 4) Admin HTML must load the same SQLite/native HTTP bridge as POS
admin_html_path = Path('capacitor/www/admin.html')
admin_html = admin_html_path.read_text()
if '<script src="sqlite-bridge.js"></script>' not in admin_html:
    admin_html = admin_html.replace('  <script src="admin.js" defer></script>', '  <script src="sqlite-bridge.js"></script>\n  <script src="admin.js" defer></script>')
admin_html = admin_html.replace("onclick=\"localStorage.removeItem('pos_logged_in');\"", "onclick=\"localStorage.removeItem('pos_logged_in'); sessionStorage.removeItem('pos_admin_logged_in');\"")
admin_html_path.write_text(admin_html)

# 5) Admin JS: use same shop-scoped SQLite storage as POS
admin_path = Path('capacitor/www/admin.js')
admin = admin_path.read_text()
api_start = admin.index('// ── API ──')
api_end = admin.index('// ── TOAST ──')
new_api = r'''// ── API ──
const ADMIN_PROFILES = {
  retail: { id:'retail', name:'Retail / Mini-Mart', icon:'🛒', item_label:'Products', tagline:'Supermarket, Grocery & General Retail POS' },
  pharmacy: { id:'pharmacy', name:'Pharmacy', icon:'💊', item_label:'Medicines', tagline:'Pharmacy & Chemist POS' },
  restaurant: { id:'restaurant', name:'Restaurant / Café', icon:'🍽️', item_label:'Menu Items', tagline:'Food, Dining & Kitchen POS' },
  hardware: { id:'hardware', name:'Hardware', icon:'🔧', item_label:'Hardware Items', tagline:'Hardware, Building Materials & Tools POS' },
  boutique: { id:'boutique', name:'Boutique / Cosmetics', icon:'👗', item_label:'Apparel & Beauty', tagline:'Fashion, Beauty & Cosmetics POS' },
  bar: { id:'bar', name:'Bar / Nightclub', icon:'🍸', item_label:'Drinks & Snacks', tagline:'Bar, Lounge & Club POS' }
};

const CLOUD_API_BASE = (localStorage.getItem('pos_cloud_api_base') || 'http://3.87.19.244:5000').replace(/\/$/, '');

const LocalAdmin = {
  type() { return localStorage.getItem('pos_active_business_type') || 'retail'; },
  key(name) { return `shop:${this.type()}:${name}`; },
  async get(name, fallback) {
    const key = this.key(name);
    try {
      if (window.OraforgeDBReady) await window.OraforgeDBReady;
      if (window.OraforgeDB) return await window.OraforgeDB.get(key, fallback);
    } catch (err) { console.warn('Admin DB read fallback', err); }
    try {
      const raw = localStorage.getItem('fallback_' + key);
      return raw == null ? fallback : JSON.parse(raw);
    } catch (_) { return fallback; }
  },
  async set(name, value) {
    const key = this.key(name);
    try {
      if (window.OraforgeDBReady) await window.OraforgeDBReady;
      if (window.OraforgeDB) { await window.OraforgeDB.set(key, value); return; }
    } catch (err) { console.warn('Admin DB write fallback', err); }
    localStorage.setItem('fallback_' + key, JSON.stringify(value));
  },
  nextId(rows) { return (rows || []).reduce((m, r) => Math.max(m, Number(r.id || 0)), 0) + 1; },
  profile() { return ADMIN_PROFILES[this.type()] || ADMIN_PROFILES.retail; },
  async settings() {
    const p = this.profile();
    return await this.get('settings', {
      business_name: p.name + ' POS', business_tagline: p.tagline, business_type: p.id,
      currency: 'KES', tax_rate: 16, receipt_footer: 'Thank you for your business!'
    });
  },
  async handle(path, opts = {}) {
    const url = new URL(path, 'https://local.pos');
    const cleanPath = url.pathname;
    const method = (opts.method || 'GET').toUpperCase();
    const body = opts.body ? (typeof opts.body === 'string' ? JSON.parse(opts.body) : opts.body) : {};
    const profile = this.profile();
    const items = await this.get('items', []);
    const cats = await this.get('categories', []);
    const orders = await this.get('orders', []);

    if (cleanPath === '/api/bootstrap') {
      return {
        user: { id:2, username:'admin', name:'The Owner', full_name:'The Owner', role:'manager', business_type:this.type() },
        settings: await this.settings(),
        profile,
        capabilities: {},
        menu: { categories: cats, items }
      };
    }

    if (cleanPath === '/api/admin/summary') {
      const paid = orders.filter(o => o.status === 'paid');
      const now = new Date();
      const todayKey = now.toISOString().slice(0,10);
      const dayKey = ts => new Date(Number(ts || 0) * 1000).toISOString().slice(0,10);
      const paidToday = paid.filter(o => dayKey(o.paid_at || o.updated_at) === todayKey);
      const salesToday = paidToday.reduce((s,o) => s + Number(o.total_cents || 0), 0);
      const weekStart = Math.floor((Date.now() - 6*86400000) / 1000);
      const paidWeek = paid.filter(o => Number(o.paid_at || o.updated_at || 0) >= weekStart);
      const salesWeek = paidWeek.reduce((s,o) => s + Number(o.total_cents || 0), 0);
      const itemMap = new Map();
      const employeeMap = new Map();
      const methodMap = new Map();
      for (const order of paidWeek) {
        const employee = order.employee_name || 'POS Terminal';
        const er = employeeMap.get(employee) || { employee, orders:0, sales:0 };
        er.orders += 1; er.sales += Number(order.total_cents || 0); employeeMap.set(employee, er);
        const method = order.payment_method || 'cash';
        const mr = methodMap.get(method) || { method, count:0, sales:0 };
        mr.count += 1; mr.sales += Number(order.total_cents || 0); methodMap.set(method, mr);
        for (const row of order.items || []) {
          const ir = itemMap.get(row.menu_item_id) || { name:row.name, qty:0, sales:0 };
          ir.qty += Number(row.qty || 0); ir.sales += Number(row.line_total_cents || 0); itemMap.set(row.menu_item_id, ir);
        }
      }
      const salesTrend = [];
      for (let i=6; i>=0; i--) {
        const d = new Date(); d.setDate(d.getDate()-i); const key = d.toISOString().slice(0,10);
        salesTrend.push({ day:key, sales: paidWeek.filter(o => dayKey(o.paid_at || o.updated_at) === key).reduce((s,o)=>s+Number(o.total_cents||0),0) });
      }
      const users = await this.get('users', [
        { id:1, username:'terminal', full_name:'POS Terminal', role:'cashier', active:1 },
        { id:2, username:'admin', full_name:'The Owner', role:'manager', active:1 }
      ]);
      const suppliers = await this.get('suppliers', []);
      return {
        totals: { paid_today:paidToday.length, sales_today:salesToday, unpaid_orders:orders.filter(o=>o.status==='open').length, unpaid_total:orders.filter(o=>o.status==='open').reduce((s,o)=>s+Number(o.total_cents||0),0), sales_week:salesWeek },
        counts: { active_users:users.filter(u=>Number(u.active ?? 1)).length, active_items:items.length, active_suppliers:suppliers.filter(s=>Number(s.active ?? 1)).length },
        by_employee:[...employeeMap.values()].sort((a,b)=>b.sales-a.sales),
        by_method:[...methodMap.values()],
        top_items:[...itemMap.values()].sort((a,b)=>b.sales-a.sales).slice(0,5),
        sales_trend:salesTrend
      };
    }

    if (cleanPath === '/api/admin/users' && method === 'GET') {
      return await this.get('users', [
        { id:1, username:'terminal', full_name:'POS Terminal', role:'cashier', active:1 },
        { id:2, username:'admin', full_name:'The Owner', role:'manager', active:1 }
      ]);
    }
    if (cleanPath === '/api/admin/user' && method === 'POST') {
      const users = await this.get('users', [
        { id:1, username:'terminal', full_name:'POS Terminal', role:'cashier', active:1 },
        { id:2, username:'admin', full_name:'The Owner', role:'manager', active:1 }
      ]);
      let user = body.id ? users.find(u => u.id === Number(body.id)) : null;
      if (!user) { user = { id:this.nextId(users) }; users.push(user); }
      Object.assign(user, { username:body.username || user.username || 'staff', full_name:body.full_name || body.name || user.full_name || 'Staff', role:body.role || 'cashier', active:Number(body.active ?? 1) });
      await this.set('users', users); return users;
    }

    if (cleanPath === '/api/menu' || cleanPath === '/api/admin/menu') return { categories:cats, items };
    if (cleanPath === '/api/menu/item' && method === 'POST') {
      const products = [...items];
      let item = body.id ? products.find(i => i.id === Number(body.id)) : null;
      if (!item) { item = { id:this.nextId(products), active:1 }; products.push(item); }
      Object.assign(item, {
        category_id:Number(body.category_id || item.category_id || cats[0]?.id || 1),
        name:body.name || item.name || 'Product',
        price_cents:Math.round(Number(body.price || (Number(item.price_cents||0)/100)) * 100),
        cost_cents:Math.round(Number(body.cost || (Number(item.cost_cents||0)/100)) * 100),
        stock_qty:Number(body.stock_qty ?? item.stock_qty ?? 0),
        sku:body.sku || item.sku || '', barcode:body.barcode || item.barcode || '',
        color:body.color || item.color || '#334155', active:Number(body.active ?? item.active ?? 1),
        unit:body.unit || item.unit || 'pcs', image_url:body.image_url || item.image_url || ''
      });
      await this.set('items', products); return { categories:cats, items:products };
    }

    if (cleanPath === '/api/admin/customers' && method === 'GET') return await this.get('customers', []);
    if (cleanPath === '/api/admin/customer' && method === 'POST') {
      const customers = await this.get('customers', []);
      let customer = body.id ? customers.find(c => c.id === Number(body.id)) : null;
      if (!customer) { customer = { id:this.nextId(customers) }; customers.push(customer); }
      Object.assign(customer, { name:body.name || customer.name || 'Customer', phone:body.phone || '', email:body.email || '', notes:body.notes || '' });
      await this.set('customers', customers); return customers;
    }

    if (cleanPath === '/api/admin/suppliers' || cleanPath === '/api/suppliers') return await this.get('suppliers', []);
    if (cleanPath === '/api/admin/supplier' && method === 'POST') {
      const suppliers = await this.get('suppliers', []);
      let supplier = body.id ? suppliers.find(s => s.id === Number(body.id)) : null;
      if (!supplier) { supplier = { id:this.nextId(suppliers) }; suppliers.push(supplier); }
      Object.assign(supplier, { name:body.name || supplier.name || 'Supplier', phone:body.phone || '', email:body.email || '', address:body.address || '', active:Number(body.active ?? 1) });
      await this.set('suppliers', suppliers); return suppliers;
    }

    if (cleanPath === '/api/stock') return items;
    if (cleanPath === '/api/stock/adjust' && method === 'POST') {
      const product = items.find(i => i.id === Number(body.product_id));
      if (!product) throw new Error('Product not found');
      product.stock_qty = Math.max(0, Number(product.stock_qty || 0) + Number(body.qty_change || 0));
      await this.set('items', items); return { ok:true, item:product };
    }

    if (cleanPath === '/api/settings' && method === 'GET') return { settings:await this.settings(), profile };
    if (cleanPath === '/api/admin/promotions') return { promotions:[], campaigns:[] };
    if (cleanPath === '/api/admin/sms/config') return { configured:false, online:true, message:'Secure SMS cloud connection not configured for this APK yet.' };
    if (cleanPath === '/api/admin/sms/send') throw new Error('SMS requires the secure cloud API connection; the Africa\'s Talking key is intentionally not stored in the APK.');

    throw new Error(`Admin feature not implemented locally: ${cleanPath}`);
  }
};

async function cloudApi(path, opts = {}) {
  if (!navigator.onLine) throw new Error('This feature needs an internet connection.');
  const method = (opts.method || 'GET').toUpperCase();
  const body = opts.body ? (typeof opts.body === 'string' ? JSON.parse(opts.body) : opts.body) : null;
  const url = CLOUD_API_BASE + path;
  if (window.OraforgeHttp?.request) {
    const response = await window.OraforgeHttp.request({ url, method, headers:{'Content-Type':'application/json','Accept':'application/json'}, data:body });
    return typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
  }
  const response = await fetch(url, { method, headers:{'Content-Type':'application/json'}, body:body ? JSON.stringify(body) : undefined });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || payload.message || `Cloud service failed (${response.status})`);
  return payload;
}

async function api(path, opts = {}) {
  if (path.startsWith('/api/admin/sms/')) {
    if (path === '/api/admin/sms/config') {
      try { return await cloudApi(path, opts); }
      catch (err) { return { configured:false, online:navigator.onLine, message:err.message }; }
    }
    return cloudApi(path, opts);
  }
  return LocalAdmin.handle(path, opts);
}

'''
admin = admin[:api_start] + new_api + admin[api_end:]

# Collapse the admin drawer after a mobile navigation tap.
admin = admin.replace("  if (section === 'stock') renderStockAdmin();\n}", "  if (section === 'stock') renderStockAdmin();\n  if (window.innerWidth <= 860) document.querySelector('.admin-shell')?.classList.add('collapsed');\n}")

# Add a real local manager login and make boot wait for it.
login_func = r'''
async function ensureAdminLogin() {
  if (sessionStorage.getItem('pos_admin_logged_in') === 'true') return true;
  return await new Promise(resolve => {
    const profile = ADMIN_PROFILES[localStorage.getItem('pos_active_business_type') || 'retail'] || ADMIN_PROFILES.retail;
    const overlay = document.createElement('div');
    overlay.id = 'adminLoginOverlay';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;background:var(--bg);display:grid;place-items:center;padding:16px;box-sizing:border-box;overflow-x:hidden;';
    overlay.innerHTML = `
      <div style="width:min(390px,100%);max-width:100%;box-sizing:border-box;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:24px;box-shadow:var(--shadow-lg);">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:22px;">
          <div style="width:48px;height:48px;border-radius:12px;background:var(--primary);color:var(--primary-fg);display:grid;place-items:center;font-size:24px;">${profile.icon}</div>
          <div><h2 style="margin:0;font-size:20px;">${profile.name} Admin</h2><div style="color:var(--muted);font-size:12px;margin-top:3px;">Manager access · local device</div></div>
        </div>
        <label class="form-label" for="adminPinInput">Manager PIN</label>
        <input id="adminPinInput" class="form-input" type="password" inputmode="numeric" pattern="[0-9]*" placeholder="Enter PIN" style="font-size:22px;text-align:center;letter-spacing:5px;padding:13px;">
        <div id="adminLoginError" style="min-height:20px;color:var(--danger);font-size:12px;font-weight:700;text-align:center;margin:8px 0;"></div>
        <button id="adminLoginBtn" class="btn btn-primary" style="width:100%;padding:12px;">Login to Admin</button>
        <a href="index.html" style="display:block;text-align:center;margin-top:14px;color:var(--muted);font-size:13px;text-decoration:none;">← Back to POS</a>
        <div style="margin-top:18px;padding-top:12px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);text-align:center;">Demo manager PIN: <strong>1234</strong></div>
      </div>`;
    document.body.appendChild(overlay);
    const input = overlay.querySelector('#adminPinInput');
    const error = overlay.querySelector('#adminLoginError');
    const submit = () => {
      if (input.value !== '1234') { error.textContent = 'Invalid manager PIN.'; input.select(); return; }
      sessionStorage.setItem('pos_admin_logged_in','true');
      overlay.remove(); resolve(true);
    };
    overlay.querySelector('#adminLoginBtn').addEventListener('click', submit);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); submit(); } });
    setTimeout(() => input.focus(), 50);
  });
}

'''
boot_marker = '// ── BOOT ──\nasync function boot() {'
if boot_marker not in admin:
    raise SystemExit('Could not find admin boot marker')
admin = admin.replace(boot_marker, '// ── BOOT ──\n' + login_func + 'async function boot() {\n  await ensureAdminLogin();')
admin = admin.replace("  if (state.user.role !== 'manager') { location.href = '/admin'; return; }", "  if (!state.user || state.user.role !== 'manager') throw new Error('Manager login required');")
admin = admin.replace("boot().catch(e => { console.error(e); });", "boot().catch(e => { console.error(e); const sec = $('#sec-dashboard'); if (sec) sec.innerHTML = `<div class=\"empty-state\"><div class=\"empty-state-icon\">⚠️</div><p>${e.message}</p></div>`; });")
admin_path.write_text(admin)

# 6) Admin mobile hardening
admin_css_path = Path('capacitor/www/admin.css')
admin_css = admin_css_path.read_text()
admin_fix = r'''

/* ── APK admin mobile hardening ──────────────────────────────────────────── */
html, body { max-width: 100%; overflow-x: hidden; }
.admin-shell, .main-content, .content-section { min-width: 0; max-width: 100%; }
@media (max-width: 860px) {
  .sidebar { width: min(86vw, 320px); max-width: 320px; }
  .main-content { width: 100%; max-width: 100vw; }
  .content-section { width: 100%; max-width: 100%; overflow-x: hidden; }
  .stats-grid { grid-template-columns: 1fr !important; }
  .page-header { gap: 12px; align-items: flex-start; }
  .page-header, .panel, .two-col, .promo-grid { min-width: 0; max-width: 100%; }
  .panel-body { min-width: 0; overflow-x: auto; }
  .toast-container { left: 12px; right: 12px; bottom: 12px; }
  .toast { min-width: 0; width: 100%; }
}
'''
if 'APK admin mobile hardening' not in admin_css:
    admin_css += admin_fix
admin_css_path.write_text(admin_css)

print('Mobile runtime fixes applied.')
