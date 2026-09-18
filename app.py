from http import cookies
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import hashlib
import json
import secrets
import sqlite3
import time
from profiles import (
    PROFILES,
    DEFAULT_SETTINGS,
    get_settings,
    save_settings,
    optimize_and_save_image,
    search_product_images,
    seed_sample_data,
)



BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "pos.sqlite3"
STATIC_DIR = BASE_DIR / "static"
HOST = __import__("os").environ.get("POS_HOST", "0.0.0.0")
PORT = int(__import__("os").environ.get("PORT") or __import__("os").environ.get("POS_PORT", "3000"))

SESSIONS = {}
CACHE = {"menu": None, "menu_ts": 0}
STORE_NAME = "NIGHTCLUB"
STORE_TAGLINE = "Bar & Club POS"


def now():
    return int(time.time())


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    return f"{salt}${digest}"


def check_password(password, stored):
    salt, digest = stored.split("$", 1)
    return hash_password(password, salt).split("$", 1)[1] == digest


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]


def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'cashier',
                password_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                name TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                color TEXT NOT NULL DEFAULT '#334155',
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_no TEXT UNIQUE NOT NULL,
                supplier_id INTEGER REFERENCES suppliers(id),
                order_type TEXT NOT NULL DEFAULT 'walk-in',
                customer_name TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                subtotal_cents INTEGER NOT NULL DEFAULT 0,
                tax_cents INTEGER NOT NULL DEFAULT 0,
                total_cents INTEGER NOT NULL DEFAULT 0,
                paid_cents INTEGER NOT NULL DEFAULT 0,
                payment_method TEXT,
                payment_ref TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                menu_item_id INTEGER REFERENCES menu_items(id),
                name TEXT NOT NULL,
                qty INTEGER NOT NULL DEFAULT 1,
                unit_price_cents INTEGER NOT NULL,
                line_total_cents INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES menu_items(id),
                qty_change INTEGER NOT NULL,
                reason TEXT NOT NULL DEFAULT 'sale',
                note TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stock_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
                product_id INTEGER NOT NULL REFERENCES menu_items(id),
                qty_received INTEGER NOT NULL,
                cost_per_unit_cents INTEGER NOT NULL,
                total_cost_cents INTEGER NOT NULL,
                date_received INTEGER NOT NULL,
                created_by INTEGER REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status, updated_at);
            CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
            CREATE INDEX IF NOT EXISTS idx_menu_items_active ON menu_items(active, category_id);
            """
        )
        # Business Settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS business_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        if conn.execute("SELECT COUNT(*) FROM business_settings").fetchone()[0] == 0:
            for k, v in DEFAULT_SETTINGS.items():
                conn.execute("INSERT INTO business_settings(key, value) VALUES (?, ?)", (k, v))

        # Categories: add business_type
        cat_cols = {row["name"] for row in conn.execute("PRAGMA table_info(categories)")}
        if "business_type" not in cat_cols:
            conn.execute("ALTER TABLE categories ADD COLUMN business_type TEXT")
            conn.execute("UPDATE categories SET business_type = 'bar' WHERE business_type IS NULL")

        # Migrate existing menu_items table — add retail columns if missing
        mi_cols = {row["name"] for row in conn.execute("PRAGMA table_info(menu_items)")}
        migrations = [
            ("sku", "ALTER TABLE menu_items ADD COLUMN sku TEXT"),
            ("barcode", "ALTER TABLE menu_items ADD COLUMN barcode TEXT"),
            ("stock_qty", "ALTER TABLE menu_items ADD COLUMN stock_qty INTEGER NOT NULL DEFAULT 0"),
            ("cost_cents", "ALTER TABLE menu_items ADD COLUMN cost_cents INTEGER NOT NULL DEFAULT 0"),
            ("unit", "ALTER TABLE menu_items ADD COLUMN unit TEXT NOT NULL DEFAULT 'pcs'"),
            ("supplier_id", "ALTER TABLE menu_items ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)"),
            ("image_url", "ALTER TABLE menu_items ADD COLUMN image_url TEXT"),
        ]
        for col, sql in migrations:
            if col not in mi_cols:
                conn.execute(sql)
                
        import os
        os.makedirs("static/uploads", exist_ok=True)
        # Migrate orders table
        o_cols = {row["name"] for row in conn.execute("PRAGMA table_info(orders)")}
        if "customer_name" not in o_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN customer_name TEXT NOT NULL DEFAULT ''")
        if "supplier_id" not in o_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)")
        if "payment_ref" not in o_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_ref TEXT")
            
        cost_updates = {
            "BE-001": 20000, "BE-002": 20000, "CO-001": 30000,
            "SP-001": 150000, "SP-002": 120000, "WI-001": 80000,
        }
        for sku, cost in cost_updates.items():
            conn.execute("UPDATE menu_items SET cost_cents = ? WHERE sku = ? AND cost_cents = 0", (cost, sku))
            
        # Migrate legacy dining_tables if it exists — we keep it for compat but don't use it
        conn.execute("CREATE TABLE IF NOT EXISTS dining_tables (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, seats INTEGER NOT NULL DEFAULT 4, active INTEGER NOT NULL DEFAULT 1)")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                notes TEXT,
                created_at INTEGER DEFAULT (cast(strftime('%s','now') as int))
            )
        ''')

        # Additional capability columns for menu_items
        cur_mi_cols = {row["name"] for row in conn.execute("PRAGMA table_info(menu_items)")}
        for col_name, sql in [
            ("reorder_level", "ALTER TABLE menu_items ADD COLUMN reorder_level INTEGER NOT NULL DEFAULT 5"),
            ("batch_no", "ALTER TABLE menu_items ADD COLUMN batch_no TEXT"),
            ("expiry_date", "ALTER TABLE menu_items ADD COLUMN expiry_date TEXT"),
            ("manufacturer", "ALTER TABLE menu_items ADD COLUMN manufacturer TEXT"),
            ("strength", "ALTER TABLE menu_items ADD COLUMN strength TEXT"),
            ("wholesale_price_cents", "ALTER TABLE menu_items ADD COLUMN wholesale_price_cents INTEGER NOT NULL DEFAULT 0"),
            ("variants_json", "ALTER TABLE menu_items ADD COLUMN variants_json TEXT DEFAULT ''"),
            ("decimal_qty_enabled", "ALTER TABLE menu_items ADD COLUMN decimal_qty_enabled INTEGER NOT NULL DEFAULT 0"),
        ]:
            if col_name not in cur_mi_cols:
                conn.execute(sql)

        # Additional columns for orders
        cur_o_cols = {row["name"] for row in conn.execute("PRAGMA table_info(orders)")}
        for col_name, sql in [
            ("table_id", "ALTER TABLE orders ADD COLUMN table_id INTEGER REFERENCES dining_tables(id)"),
            ("pricing_tier", "ALTER TABLE orders ADD COLUMN pricing_tier TEXT NOT NULL DEFAULT 'retail'"),
            ("is_quote", "ALTER TABLE orders ADD COLUMN is_quote INTEGER NOT NULL DEFAULT 0"),
            ("notes", "ALTER TABLE orders ADD COLUMN notes TEXT NOT NULL DEFAULT ''"),
        ]:
            if col_name not in cur_o_cols:
                conn.execute(sql)

        # Additional columns for order_items
        cur_oi_cols = {row["name"] for row in conn.execute("PRAGMA table_info(order_items)")}
        for col_name, sql in [
            ("variant_info", "ALTER TABLE order_items ADD COLUMN variant_info TEXT NOT NULL DEFAULT ''"),
            ("batch_no", "ALTER TABLE order_items ADD COLUMN batch_no TEXT NOT NULL DEFAULT ''"),
        ]:
            if col_name not in cur_oi_cols:
                conn.execute(sql)

        # Seed sample data for profiles
        seed_sample_data(conn)

        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO users(username, full_name, role, password_hash) VALUES (?, ?, ?, ?)",
                ("terminal", "POS Terminal", "terminal", hash_password("1234")),
            )
            conn.execute(
                "INSERT INTO users(username, full_name, role, password_hash) VALUES (?, ?, ?, ?)",
                ("admin", "The Owner", "manager", hash_password("admin123")),
            )
        else:
            terminal = conn.execute("SELECT id FROM users WHERE username = 'terminal'").fetchone()
            if not terminal:
                conn.execute(
                    "INSERT INTO users(username, full_name, role, password_hash) VALUES (?, ?, ?, ?)",
                    ("terminal", "POS Terminal", "terminal", hash_password("1234")),
                )
            conn.execute("UPDATE users SET active = 1, role = 'terminal' WHERE username = 'terminal'")

            admin = conn.execute("SELECT id, password_hash FROM users WHERE username = 'admin'").fetchone()
            if not admin:
                conn.execute(
                    "INSERT INTO users(username, full_name, role, password_hash) VALUES (?, ?, ?, ?)",
                    ("admin", "The Owner", "manager", hash_password("admin123")),
                )
            else:
                conn.execute(
                    "UPDATE users SET full_name = 'The Owner', role = 'manager' WHERE id = ?",
                    (admin["id"],),
                )
            
            # Clean up old dummy staff
            conn.execute("DELETE FROM users WHERE username != 'terminal' AND username != 'admin'")

        if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
            seed_categories = ["Beers", "Cocktails", "Spirits", "Wines", "Soft Drinks", "Snacks"]
            for i, name in enumerate(seed_categories):
                conn.execute("INSERT INTO categories(name, sort_order) VALUES (?, ?)", (name, i))

            cat_ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM categories")}
            seed_items = [
                ("Beers",       "Tusker Lager 500ml", 250, 200,  "#d97706", "BE-001", 120, "btl"),
                ("Beers",       "Guinness 500ml",     300, 240,  "#1e293b", "BE-002", 80,  "btl"),
                ("Beers",       "White Cap 500ml",    250, 200,  "#94a3b8", "BE-003", 100, "btl"),
                ("Beers",       "Heineken",           350, 280,  "#15803d", "BE-004", 60,  "btl"),
                ("Cocktails",   "Mojito",             600, 300,  "#22c55e", "CO-001", 0,   "glass"),
                ("Cocktails",   "Margarita",          650, 320,  "#eab308", "CO-002", 0,   "glass"),
                ("Cocktails",   "Long Island",        800, 400,  "#ef4444", "CO-003", 0,   "glass"),
                ("Spirits",     "Jameson 750ml",     3500,2800,  "#166534", "SP-001", 12,  "btl"),
                ("Spirits",     "Gilbeys Gin 750ml", 1800,1400,  "#0ea5e9", "SP-002", 15,  "btl"),
                ("Spirits",     "Smirnoff Vodka",    1600,1200,  "#ef4444", "SP-003", 20,  "btl"),
                ("Spirits",     "Jack Daniels",      4500,3600,  "#000000", "SP-004", 8,   "btl"),
                ("Wines",       "Four Cousins Sweet",1200, 900,  "#db2777", "WI-001", 24,  "btl"),
                ("Wines",       "Nederburg Cabernet",1800,1400,  "#9d174d", "WI-002", 10,  "btl"),
                ("Soft Drinks", "Coca Cola 300ml",     80,  50,  "#dc2626", "SD-001", 60,  "btl"),
                ("Soft Drinks", "Sprite 300ml",        80,  50,  "#16a34a", "SD-002", 48,  "btl"),
                ("Soft Drinks", "Red Bull",           250, 180,  "#2563eb", "SD-003", 24,  "can"),
                ("Snacks",      "Roasted Peanuts",    100,  60,  "#d97706", "SN-001", 30,  "pkt"),
                ("Snacks",      "Potato Crisps",      150, 100,  "#f59e0b", "SN-002", 20,  "pkt"),
            ]
            for category, name, price, cost, color, sku, stock, unit in seed_items:
                conn.execute(
                    "INSERT INTO menu_items(category_id, name, price_cents, cost_cents, color, sku, stock_qty, unit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (cat_ids[category], name, price * 100, cost * 100, color, sku, stock, unit),
                )

        if conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] == 0:
            seed_suppliers = [
                ("East African Breweries Ltd", "+254 700 111 000", "orders@eabl.co.ke"),
                ("Coca-Cola Beverages Africa", "+254 722 222 111", "supply@ccba.co.ke"),
                ("KWAL Kenya", "+254 711 333 000", "procurement@kwal.co.ke"),
                ("Local Liquor Distributors", "+254 733 444 000", "sales@lld.co.ke"),
            ]
            for name, phone, email in seed_suppliers:
                conn.execute("INSERT INTO suppliers(name, phone, email) VALUES (?, ?, ?)", (name, phone, email))


def money(cents):
    return f"{cents / 100:.2f}"


def recalc_order(conn, order_id):
    subtotal = conn.execute(
        "SELECT COALESCE(SUM(line_total_cents), 0) FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchone()[0]
    tax = round(subtotal * 0.0)
    total = subtotal + tax
    conn.execute(
        "UPDATE orders SET subtotal_cents = ?, tax_cents = ?, total_cents = ?, updated_at = ? WHERE id = ?",
        (subtotal, tax, total, now(), order_id),
    )


def next_ticket(conn):
    return f"R{now()}{conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0] + 1:03d}"


def get_order_payload(conn, order_id):
    order = conn.execute(
        """
        SELECT o.*, u.full_name AS employee_name, u.username AS employee_username,
               t.name AS table_name
        FROM orders o
        LEFT JOIN users u ON u.id = o.created_by
        LEFT JOIN dining_tables t ON t.id = o.table_id
        WHERE o.id = ?
        """,
        (order_id,),
    ).fetchone()
    if not order:
        return None
    items = rows(conn.execute("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)))
    payload = dict(order)
    payload["items"] = items
    payload["total"] = money(payload["total_cents"])
    return payload


def receipt_page(order, autoprint=False, is_kot=False, settings=None):
    if not settings:
        with db() as conn:
            settings = get_settings(conn)
    bname = settings.get("business_name", "POS")
    btag = settings.get("business_tagline", "")
    phone = settings.get("phone", "")
    address = settings.get("address", "")
    r_header = settings.get("receipt_header", "Welcome to our store")
    r_footer = settings.get("receipt_footer", "Thank you for your visit!\n------- END OF RECEIPT -------")

    if is_kot:
        item_rows = "".join(
            f'''
            <tr>
              <td><strong>{item['qty']} x {item['name']}</strong>{f"<br><small style='color:#666'>* {item['note']}</small>" if item.get('note') else ""}{f"<br><small style='color:#666'>[{item['variant_info']}]</small>" if item.get('variant_info') else ""}</td>
            </tr>
            '''
            for item in order["items"]
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>KOT #{order['ticket_no']} — {bname}</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body class="receipt-body">
  <section class="receipt">
    <h1>*** KITCHEN / BAR ORDER ***</h1>
    <p>Ticket: <strong>#{order['ticket_no']}</strong></p>
    <div style="border-top: 2px dashed var(--line); margin: 10px 0;"></div>
    <div class="receipt-line"><span>Table / Tab</span><strong>{order.get('table_name') or 'Counter'}</strong></div>
    <div class="receipt-line"><span>Server</span><strong>{order.get('employee_name') or '-'}</strong></div>
    <div class="receipt-line"><span>Time</span><strong>{__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</strong></div>
    {f"<div class='receipt-line'><span>Notes</span><strong>{order.get('notes')}</strong></div>" if order.get('notes') else ""}
    <div style="border-top: 2px dashed var(--line); margin: 10px 0;"></div>
    <table><tbody>{item_rows}</tbody></table>
    <div style="border-top: 2px dashed var(--line); margin: 10px 0;"></div>
    <button onclick="window.print()">Print KOT</button>
  </section>
  {"<script>window.addEventListener('load', () => setTimeout(() => window.print(), 250));</script>" if autoprint else ""}
</body>
</html>"""

    is_quote = bool(order.get("is_quote") or order.get("order_type") == "quote")
    title_label = "QUOTATION / ESTIMATE" if is_quote else "ORIGINAL RECEIPT"

    item_rows = "".join(
        f'''
        <tr>
          <td>
            {item['qty']} x {item['name']}
            {f"<br><small style='color:#666'>Variant: {item['variant_info']}</small>" if item.get('variant_info') else ""}
            {f"<br><small style='color:#666'>Batch: {item['batch_no']}</small>" if item.get('batch_no') else ""}
            {f"<br><small style='color:#666'>Note: {item['note']}</small>" if item.get('note') else ""}
          </td>
          <td style="text-align:right;">{money(item['line_total_cents'])}</td>
        </tr>
        '''
        for item in order["items"]
    )

    vat_rate = float(settings.get("tax_rate", 16.0))
    vat_multiplier = 1.0 + (vat_rate / 100.0) if vat_rate > 0 else 1.0
    subtotal_no_vat = (order['total_cents'] / vat_multiplier) / 100
    vat_amount = (order['total_cents'] - (order['total_cents'] / vat_multiplier)) / 100

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{'Quote' if is_quote else 'Receipt'} #{order['ticket_no']} — {bname}</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body class="receipt-body">
  <section class="receipt">
    <h1>{bname}</h1>
    {f"<p style='font-weight:600;'>{btag}</p>" if btag else ""}
    {f"<p>{address}</p>" if address else ""}
    {f"<p>Tel: {phone}</p>" if phone else ""}
    <h2 style="font-size: 15px; margin: 12px 0 8px; font-weight: 800;">* {title_label} *</h2>
    <div class="receipt-line"><span>Date</span><strong>{__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}</strong></div>
    <div class="receipt-line"><span>Ref #</span><strong>{order['ticket_no']}</strong></div>
    {f"<div class='receipt-line'><span>Table / Tab</span><strong>{order.get('table_name')}</strong></div>" if order.get('table_name') else ""}
    <div class="receipt-line"><span>Type</span><strong>{order['order_type'].upper()}</strong></div>
    <div class="receipt-line"><span>Served By</span><strong>{order.get('employee_name') or '-'}</strong></div>
    {f"<div class='receipt-line'><span>Customer</span><strong>{order.get('customer_name')}</strong></div>" if order.get('customer_name') else ""}
    <div class="receipt-line"><span>Status</span><strong>{order['status'].upper()}</strong></div>
    <div style="border-top: 1px dashed var(--line); margin: 10px 0;"></div>
    <table>
      <tbody>{item_rows}</tbody>
    </table>
    <div style="border-top: 1px dashed var(--line); margin: 10px 0;"></div>
    <div class="receipt-total"><span>Total</span><strong>KES {order['total']}</strong></div>
    {"" if is_quote else f'''
    <div class="receipt-line"><span>Amount Tendered</span><strong>KES {order['total']}</strong></div>
    <div class="receipt-line"><span>Change</span><strong>KES 0.00</strong></div>
    <div style="border-top: 1px dashed var(--line); margin: 10px 0;"></div>
    <div class="receipt-line"><span>Total Excl. VAT</span><strong>KES {subtotal_no_vat:,.2f}</strong></div>
    <div class="receipt-line"><span>Total VAT ({vat_rate:.0f}%)</span><strong>KES {vat_amount:,.2f}</strong></div>
    <div style="border-top: 1px dashed var(--line); margin: 10px 0;"></div>
    <div class="receipt-line"><span>Payment Method</span><strong>{(order.get('payment_method') or 'CASH').upper()}</strong></div>
    <div class="receipt-line"><span>Txn Ref</span><strong>{order.get('payment_ref') or f"TXN-{order['id'] * 1234}"}</strong></div>
    '''}
    <p class="receipt-note" style="line-height: 1.6; margin-top: 12px; white-space: pre-wrap;">{r_footer}</p>
    <button onclick="window.print()">Print {'Quote' if is_quote else 'Receipt'}</button>
  </section>
  {"<script>window.addEventListener('load', () => setTimeout(() => window.print(), 250));</script>" if autoprint else ""}
</body>
</html>"""

def hidden_admin_page():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Admin Portal — EITY FIT</title>
  <link rel="stylesheet" href="/static/admin.css?v=1782846743.6849699">
  <script>
    (function() {
      var t = localStorage.getItem('pos_theme') || 'light';
      document.documentElement.setAttribute('data-theme', t);
    })();
  </script>
</head>
<body>
  <div class="admin-shell">
    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="logo">
          <div class="logo-icon">B</div>
          <span class="name">EITY FIT</span>
        </div>
        <div class="tag">Admin Portal</div>
        <button class="sidebar-toggle" id="sidebarToggle" title="Toggle sidebar">
          <span></span><span></span><span></span>
        </button>
      </div>
      <nav class="sidebar-nav">
        <div class="nav-item active" data-section="dashboard">
          <span class="nav-icon">&#9646;</span>
          <span class="nav-label">Dashboard</span>
        </div>
        <div class="nav-item" data-section="users">
          <span class="nav-icon">&#9646;</span>
          <span class="nav-label">Staff</span>
        </div>
        <div class="nav-item" data-section="menu">
          <span class="nav-icon">&#9646;</span>
          <span class="nav-label">Products</span>
        </div>
        <div class="nav-item" data-section="customers">
          <span class="nav-icon">&#9646;</span>
          <span class="nav-label">Customers</span>
        </div>
        <div class="nav-item" data-section="promotions">
          <span class="nav-icon">&#9646;</span>
          <span class="nav-label">WhatsApp Promotions</span>
        </div>
        <div class="nav-item" data-section="pos">
          <span class="nav-icon">&#9646;</span>
          <span class="nav-label">Back to POS</span>
        </div>
      </nav>
      <div class="sidebar-footer">
        <div class="user-card">
          <div class="user-avatar" id="userAvatarLetter">A</div>
          <div class="user-info">
            <div class="user-name" id="userDisplayName">Admin</div>
            <div class="user-role">Manager</div>
          </div>
        </div>
        <a class="logout-btn" href="/logout">Logout</a>
      </div>
    </aside>

    <!-- MAIN -->
    <main class="main-content">
      <div class="content-section active" id="sec-dashboard"></div>
      <div class="content-section" id="sec-users"></div>
      <div class="content-section" id="sec-menu"></div>
      <div class="content-section" id="sec-customers"></div>
      <div class="content-section" id="sec-promotions"></div>
    </main>
  </div>

  <!-- FLOATING OPEN BUTTON (shown when sidebar is collapsed) -->
  <button class="sidebar-open-btn" id="sidebarOpenBtn" title="Open sidebar">
    <span></span><span></span><span></span>
  </button>

  <!-- TOAST CONTAINER -->
  <div class="toast-container" id="toastContainer"></div>

  <script src="/static/admin.js?v=1782848139.5770284" defer></script>
  <script>
    document.addEventListener('DOMContentLoaded', () => {
      const shell = document.querySelector('.admin-shell');
      const closeBtn = document.getElementById('sidebarToggle');
      const openBtn = document.getElementById('sidebarOpenBtn');
      if (window.innerWidth <= 860) shell.classList.add('collapsed');
      closeBtn.addEventListener('click', () => shell.classList.add('collapsed'));
      openBtn.addEventListener('click', () => shell.classList.remove('collapsed'));
    });
  </script>
</body>
</html>"""


def page(title, active, content, role=None, settings=None):
    if not settings:
        with db() as conn:
            settings = get_settings(conn)
    btype = settings.get("business_type", "bar")
    profile = PROFILES.get(btype, PROFILES["retail"])
    bname = settings.get("business_name", "POS")
    btag = settings.get("business_tagline", profile["tagline"])
    bicon = profile.get("icon", "🛒")

    nav = [
        ("🖥️", "POS", "/pos"),
        ("🚚", "Suppliers", "/suppliers"),
        ("🧾", "Sales", "/sales"),
        ("📦", "Products", "/products"),
        ("📊", "Reports", "/reports"),
        ("⚙️", "Settings", "/settings"),
    ]
    links = "".join(
        f'<a class="nav-link {"active" if active == label else ""}" href="{href}"><span class="nav-icon">{icon}</span>{label}</a>'
        for icon, label, href in nav
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — {bname}</title>
  <link rel="stylesheet" href="/static/inter.css">
  <link rel="stylesheet" href="/static/styles.css?v={int(time.time())}">
  <script>
    (function() {{
      var t = localStorage.getItem('pos_theme') || 'light';
      document.documentElement.setAttribute('data-theme', t);
    }})();
  </script>
</head>
<body>
  <header class="topbar">
    <div class="topbar-left">
      <button class="mobile-nav-toggle" id="mobileNavToggle">
        <span></span><span></span><span></span>
      </button>
      <a class="brand" href="/pos">
        <div class="brand-logo">{bicon}</div>
        <div class="brand-text">
          <span id="brandName">{bname}</span>
          <small id="brandTagline">{btag}</small>
        </div>
      </a>
      <div class="topbar-divider"></div>
    </div>
    <div class="topbar-center">
      <nav id="topNav">{links}</nav>
    </div>
    <div class="topbar-right">
      <span class="status-dot" title="System online"></span>
      <div class="topbar-clock">
        <span id="navTime">--:--</span>
        <span id="navDate">---</span>
      </div>
      <button id="themeToggleBtn" class="theme-toggle-btn" title="Toggle Light / Dark theme" aria-label="Toggle theme">☀️</button>
      <div class="topbar-divider"></div>
      <a class="logout" href="/logout">⏏ Logout</a>
    </div>
  </header>
  <main>{content}</main>
  <script src="/static/app.js?v={int(time.time())}" defer></script>
  <script>
    function updateClock() {{
      const now = new Date();
      const t = now.toLocaleTimeString('en-GB', {{hour:'2-digit', minute:'2-digit', second:'2-digit'}});
      const d = now.toLocaleDateString('en-GB', {{weekday:'short', day:'2-digit', month:'short'}});
      const te = document.getElementById('navTime');
      const de = document.getElementById('navDate');
      if (te) te.textContent = t;
      if (de) de.textContent = d;
    }}
    updateClock();
    setInterval(updateClock, 1000);

    document.addEventListener('DOMContentLoaded', () => {{
      const toggle = document.getElementById('mobileNavToggle');
      const center = document.querySelector('.topbar-center');
      if(toggle && center) {{
        toggle.addEventListener('click', (e) => {{ e.stopPropagation(); center.classList.toggle('open'); }});
        document.addEventListener('click', (e) => {{
          if (!center.contains(e.target) && !toggle.contains(e.target)) center.classList.remove('open');
        }});
      }}
    }});
  </script>
</body>
</html>"""

def employee_login_page(error="", settings=None):
    if not settings:
        with db() as conn:
            settings = get_settings(conn)
    btype = settings.get("business_type", "bar")
    profile = PROFILES.get(btype, PROFILES["retail"])
    bname = settings.get("business_name", profile["name"])
    btag = settings.get("business_tagline", profile["tagline"])
    bicon = profile.get("icon", "🏢")

    chips = []
    for k, p in PROFILES.items():
        is_active = (k == btype)
        if is_active:
            style = "background:var(--primary); color:var(--primary-fg); border:1px solid var(--primary); font-weight:700; box-shadow:0 1px 3px rgba(0,0,0,0.15);"
            mark = " ✓"
        else:
            style = "background:var(--panel); color:var(--ink); border:1px solid var(--line);"
            mark = ""
        chips.append(f"""
          <button type="submit" name="switch_business_type" value="{k}" class="shop-chip" style="{style} padding:8px 10px; border-radius:8px; font-size:12px; cursor:pointer; display:flex; align-items:center; gap:6px; text-align:left; transition:all 0.15s ease;">
            <span style="font-size:18px;">{p['icon']}</span>
            <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{p['name']}{mark}</span>
          </button>
        """)
    chips_html = "\n".join(chips)

    message = f'<p class="error" style="text-align:center; margin:0 0 8px;">{error}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Staff Login — {bname} POS</title>
  <link rel="stylesheet" href="/static/styles.css?v={now()}">
  <script>
    (function() {{
      var t = localStorage.getItem('pos_theme') || 'light';
      document.documentElement.setAttribute('data-theme', t);
    }})();
  </script>
</head>
<body class="login-body">
  <div style="position:fixed; top:18px; right:18px; z-index:1000;">
    <button id="themeToggleBtn" class="theme-toggle-btn" style="width:40px; height:40px; font-size:18px;" title="Toggle Light / Dark theme">☀️</button>
  </div>

  <form class="login-panel" method="post" action="/login">
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:4px;">
      <div style="width:48px; height:48px; border-radius:12px; background:var(--ink); display:grid; place-items:center; font-size:26px; flex-shrink:0; box-shadow:0 2px 8px rgba(0,0,0,0.15); color:var(--panel);">
        {bicon}
      </div>
      <div>
        <h1 style="margin:0; font-size:21px; font-weight:800; color:var(--ink);">{bname} POS</h1>
        <p style="margin:2px 0 0; color:var(--muted); font-size:12px;">{btag}</p>
      </div>
    </div>

    <div style="background:var(--bg); border:1px solid var(--line); border-radius:10px; padding:12px; margin:4px 0;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
        <span style="font-size:11px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px;">🏢 Select Shop Category</span>
        <span style="font-size:11px; color:var(--muted); font-weight:600;">1-Click Switch</span>
      </div>
      <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:6px;">
        {chips_html}
      </div>
    </div>

    {message}

    <button type="submit" name="quick_login" value="1" id="quickLoginBtn" style="width:100%; padding:12px; background:var(--primary); color:var(--primary-fg); border-radius:8px; font-weight:700; font-size:14px; border:1px solid var(--primary); cursor:pointer; display:flex; align-items:center; justify-content:center; gap:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
      <span>⚡</span> 1-Click Demo Login (PIN: 1234)
    </button>

    <div style="display:flex; align-items:center; gap:10px; margin:2px 0;">
      <div style="flex:1; height:1px; background:var(--line);"></div>
      <span style="font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px;">or enter pin on keypad</span>
      <div style="flex:1; height:1px; background:var(--line);"></div>
    </div>

    <input id="pinInput" name="pin" type="password" inputmode="numeric" pattern="[0-9]*" value="" autocomplete="current-password" autofocus placeholder="Staff PIN" style="text-align:center; font-size:22px; letter-spacing:4px; font-weight:700;">
    <div class="pin-pad" data-pin-pad>
      <button type="button" data-key="1">1</button>
      <button type="button" data-key="2">2</button>
      <button type="button" data-key="3">3</button>
      <button type="button" data-key="4">4</button>
      <button type="button" data-key="5">5</button>
      <button type="button" data-key="6">6</button>
      <button type="button" data-key="7">7</button>
      <button type="button" data-key="8">8</button>
      <button type="button" data-key="9">9</button>
      <button type="button" data-key="clear">Clear</button>
      <button type="button" data-key="0">0</button>
      <button type="submit">Enter</button>
    </div>
    <small style="text-align:center; display:block; font-size:12px; color:var(--muted); line-height:1.4;">
      Staff PIN: <strong>1234</strong> • Single codebase supporting all 6 profiles.<br>
      Choose category above to explore tailored features & sample catalog.
    </small>
  </form>
  <script>
    const pinInput = document.getElementById('pinInput');
    document.querySelectorAll('[data-pin-pad] button[data-key]').forEach((button) => {{
      button.addEventListener('click', () => {{
        const key = button.dataset.key;
        if (key === 'clear') pinInput.value = '';
        else if (pinInput.value.length < 6) pinInput.value += key;
        pinInput.focus();
      }});
    }});

    const themeBtn = document.getElementById('themeToggleBtn');
    if (themeBtn) {{
      const cur = document.documentElement.getAttribute('data-theme') || 'light';
      themeBtn.textContent = cur === 'dark' ? '☀️' : '🌙';
      themeBtn.title = cur === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme';
      themeBtn.addEventListener('click', () => {{
        const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('pos_theme', next);
        themeBtn.textContent = next === 'dark' ? '☀️' : '🌙';
        themeBtn.title = next === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme';
      }});
    }}
  </script>
</body>
</html>"""


def cashier_login_page(error=""):
    message = f'<p class="error">{error}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cashier Login — {STORE_NAME} POS</title>
  <link rel="stylesheet" href="/static/styles.css?v={int(time.time())}">
  <script>
    (function() {{
      var t = localStorage.getItem('pos_theme') || 'light';
      document.documentElement.setAttribute('data-theme', t);
    }})();
  </script>
</head>
<body class="login-body">
  <form class="login-panel" method="post" action="/cashier">
    <h1>Cashier Portal</h1>
    <p>Username and password required</p>
    {message}
    <label>Username<input name="username" autocomplete="username" autofocus></label>
    <label>Password<input name="password" type="password" autocomplete="current-password"></label>
    <button type="submit">Log In</button>
    <small>Default: admin / admin123</small>
  </form>
</body>
</html>"""


def admin_login_page(error=""):
    message = f'<p class="error">{error}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Admin Login — {STORE_NAME}</title>
  <link rel="stylesheet" href="/static/admin.css?v={int(time.time())}">
  <script>
    (function() {{
      var t = localStorage.getItem('pos_theme') || 'light';
      document.documentElement.setAttribute('data-theme', t);
    }})();
  </script>
  <style>
    body {{ display:grid; place-items:center; min-height:100vh; background:var(--bg); }}
    .admin-login-panel {{
      width: min(380px, calc(100vw - 32px));
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow-lg);
      padding: 36px;
      display: grid;
      gap: 18px;
    }}
    .admin-login-panel .brand {{
      display:flex; align-items:center; gap:10px; margin-bottom:4px;
    }}
    .admin-login-panel .logo-icon {{
      width:38px; height:38px; background:var(--primary);
      border-radius:9px; display:grid; place-items:center;
      font-size:18px; font-weight:900; color:#fff;
    }}
    .admin-login-panel h2 {{ margin:0; font-size:20px; font-weight:800; color:var(--navy); }}
    .admin-login-panel p {{ margin:0; color:var(--muted); font-size:13px; }}
    .admin-login-panel .err {{ color:var(--danger); font-weight:700; font-size:13px; }}
  </style>
</head>
<body>
  <form class="admin-login-panel" method="post" action="/admin">
    <div class="brand">
      <div class="logo-icon">B</div>
      <div>
        <h2>{STORE_NAME} Admin</h2>
        <p>Restricted access</p>
      </div>
    </div>
    {message}
    <div class="form-group">
      <label class="form-label">Username</label>
      <input class="form-input" name="username" autocomplete="username" autofocus placeholder="admin">
    </div>
    <div class="form-group">
      <label class="form-label">Password</label>
      <input class="form-input" name="password" type="password" autocomplete="current-password" placeholder="••••••••">
    </div>
    <button class="btn btn-primary" type="submit" style="width:100%;justify-content:center;padding:12px">Sign In</button>
  </form>
</body>
</html>"""


class POSHandler(SimpleHTTPRequestHandler):
    server_version = "NIGHTCLUBPOS/1.0"

    def log_message(self, format, *args):
        return

    def end_headers(self):
        # Cache static assets aggressively (1 hour)
        if hasattr(self, 'path') and self.path.startswith("/static/"):
            self.send_header("Cache-Control", "public, max-age=3600")
        super().end_headers()

    def send_html(self, html, status=200):
        data = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload, status=200):
        data = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return json.loads(raw or b"{}")
        return {k: v[0] for k, v in parse_qs(raw.decode()).items()}

    def session_user(self):
        header = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie(header)
        sid = jar.get("sid")
        return SESSIONS.get(sid.value) if sid else None

    def require_user(self):
        user = self.session_user()
        if user:
            return user
        if self.path.startswith("/api/"):
            self.send_json({"error": "login_required"}, 401)
        else:
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
        return None

    def require_cashier(self, user):
        if user.get("role") in ("manager", "cashier"):
            return True
        if self.path.startswith("/api/"):
            self.send_json({"error": "cashier_login_required"}, 403)
        else:
            self.send_html(page("Cashier Required", "", '<section class="empty">Cashier login required for this page</section>'), 403)
        return False

    def require_manager(self, user):
        if user.get("role") == "manager":
            return True
        if self.path.startswith("/api/"):
            self.send_json({"error": "manager_login_required"}, 403)
        else:
            self.send_html(page("Admin Required", "", '<section class="empty">Admin manager login required for this page</section>'), 403)
        return False

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/static/"):
            self.directory = str(BASE_DIR)
            # Send with aggressive cache headers for CSS/JS/fonts
            result = super().do_GET()
            return result
        if path in ("/", "/login"):
            if self.session_user():
                self.send_response(302)
                self.send_header("Location", "/pos")
                self.end_headers()
            else:
                with db() as conn:
                    settings = get_settings(conn)
                self.send_html(employee_login_page(settings=settings))
            return
        if path == "/cashier":
            user = self.session_user()
            if user and user.get("role") in ("manager", "cashier"):
                # Authenticated cashier — show the payments page directly
                self.send_html(page("Cashier", "Cashier", '<section class="page-shell" data-page="cashier"></section>', user.get("role")))
            else:
                self.send_html(cashier_login_page())
            return
        if path == "/logout":
            sid = cookies.SimpleCookie(self.headers.get("Cookie", "")).get("sid")
            if sid:
                SESSIONS.pop(sid.value, None)
            self.send_response(302)
            self.send_header("Set-Cookie", "sid=; Max-Age=0; Path=/")
            self.send_header("Location", "/login")
            self.end_headers()
            return

        if path == "/secret-admin":
            user = self.session_user()
            if not user:
                self.send_html(admin_login_page())
                return
            if user.get("role") != "manager":
                self.send_html(admin_login_page("Access denied: manager account required"), 403)
                return
            self.send_html(hidden_admin_page())
            return

        if path == "/admin":
            user = self.session_user()
            if not user:
                self.send_html(admin_login_page())
                return
            if user.get("role") != "manager":
                self.send_html(admin_login_page("Access denied: manager account required"), 403)
                return
            self.send_html(hidden_admin_page())
            return

        user = self.require_user()
        if not user:
            return

        if path.startswith("/api/"):
            return self.api_get(path, parse_qs(parsed.query), user)

        if path == "/receipt":
            order_id = parse_qs(parsed.query).get("order_id", [""])[0]
            if not order_id.isdigit():
                self.send_html(page("Receipt", "", '<section class="empty">Missing order id</section>'), 400)
                return
            with db() as conn:
                order = get_order_payload(conn, int(order_id))
                settings = get_settings(conn)
            if not order:
                self.send_html(page("Receipt", "", '<section class="empty">Order not found</section>'), 404)
                return
            autoprint = parse_qs(parsed.query).get("print", ["0"])[0] == "1"
            is_kot = parse_qs(parsed.query).get("kot", ["0"])[0] == "1"
            self.send_html(receipt_page(order, autoprint, is_kot=is_kot, settings=settings))
            return

        pages = {
            "/pos": ("POS", "POS", '<section class="pos-shell" data-page="pos"></section>'),
            "/suppliers": ("Suppliers", "Suppliers", '<section class="page-shell" data-page="suppliers"></section>'),
            "/sales": ("Sales", "Sales", '<section class="page-shell" data-page="sales"></section>'),
            "/products": ("Products", "Products", '<section class="page-shell" data-page="products"></section>'),
            "/customers": ("Customers", "Customers", '<section class="page-shell" data-page="customers"></section>'),
            "/reports": ("Reports", "Reports", '<section class="page-shell" data-page="reports"></section>'),
            "/settings": ("Settings", "Settings", '<section class="page-shell" data-page="settings"></section>'),
        }
        if path in pages:
            title, active, content = pages[path]
            self.send_html(page(title, active, content, user.get("role")))
            return
        self.send_html(page("Not Found", "", '<section class="empty">Page not found</section>'), 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        method = self.command
        if path == "/login":
            data = self.read_body()
            switch_to = data.get("switch_business_type")
            if switch_to and switch_to in PROFILES:
                prof = PROFILES[switch_to]
                with db() as conn:
                    save_settings(conn, {
                        "business_type": switch_to,
                        "business_name": prof.get("name", switch_to),
                        "business_tagline": prof.get("tagline", ""),
                    })
                CACHE.clear()
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            if str(data.get("quick_login", "")).strip() in ("1", "true"):
                pin = "1234"
            else:
                pin = data.get("pin", "")

            user = None
            with db() as conn:
                user = conn.execute("SELECT * FROM users WHERE username = 'terminal' AND active = 1").fetchone()
            if user and not check_password(pin, user["password_hash"]):
                user = None
            if user:
                sid = secrets.token_urlsafe(32)
                SESSIONS[sid] = {"id": user["id"], "username": user["username"], "role": user["role"], "name": user["full_name"]}
                self.send_response(302)
                self.send_header("Set-Cookie", f"sid={sid}; HttpOnly; SameSite=Lax; Path=/")
                self.send_header("Location", "/pos")
                self.end_headers()
            else:
                with db() as conn:
                    settings = get_settings(conn)
                self.send_html(employee_login_page("Invalid PIN", settings=settings), 401)
            return
        if path == "/cashier":
            data = self.read_body()
            with db() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE username = ? AND role IN ('manager', 'cashier') AND active = 1",
                    (data.get("username", ""),),
                ).fetchone()
            if user and check_password(data.get("password", ""), user["password_hash"]):
                sid = secrets.token_urlsafe(32)
                SESSIONS[sid] = {"id": user["id"], "username": user["username"], "role": user["role"], "name": user["full_name"]}
                self.send_response(302)
                self.send_header("Set-Cookie", f"sid={sid}; HttpOnly; SameSite=Lax; Path=/")
                self.send_header("Location", "/cashier")
                self.end_headers()
            else:
                self.send_html(cashier_login_page("Invalid username or password"), 401)
            return
        if path == "/admin":
            data = self.read_body()
            with db() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE username = ? AND role = 'manager' AND active = 1",
                    (data.get("username", ""),),
                ).fetchone()
            if user and check_password(data.get("password", ""), user["password_hash"]):
                sid = secrets.token_urlsafe(32)
                SESSIONS[sid] = {"id": user["id"], "username": user["username"], "role": user["role"], "name": user["full_name"]}
                self.send_response(302)
                self.send_header("Set-Cookie", f"sid={sid}; HttpOnly; SameSite=Lax; Path=/")
                self.send_header("Location", "/admin")
                self.end_headers()
            else:
                self.send_html(admin_login_page("Invalid credentials or insufficient permissions"), 401)
            return

        user = self.require_user()
        if not user:
            return
        if path.startswith("/api/"):
            return self.api_post(path, self.read_body(), user, method, query)
        self.send_json({"error": "not_found"}, 404)

    def api_get(self, path, query, user):
        with db() as conn:
            if path == "/api/bootstrap":
                settings = get_settings(conn)
                btype = settings.get("business_type", "bar")
                profile = PROFILES.get(btype, PROFILES["retail"])

                expiry_alerts = 0
                if profile["capabilities"].get("batches_expiry"):
                    future_str = (__import__('datetime').date.today() + __import__('datetime').timedelta(days=60)).isoformat()
                    expiry_alerts = conn.execute(
                        "SELECT COUNT(*) FROM menu_items WHERE active = 1 AND expiry_date IS NOT NULL AND expiry_date != '' AND expiry_date <= ?",
                        (future_str,)
                    ).fetchone()[0]

                low_stock_alerts = 0
                if profile["capabilities"].get("reorder_levels"):
                    low_stock_alerts = conn.execute(
                        "SELECT COUNT(*) FROM menu_items WHERE active = 1 AND stock_qty <= reorder_level"
                    ).fetchone()[0]

                tables = self.tables_payload(conn) if profile["capabilities"].get("tables") else []

                self.send_json({
                    "user": user,
                    "settings": settings,
                    "profile": profile,
                    "profiles": PROFILES,
                    "capabilities": profile["capabilities"],
                    "employees": self.employees_payload(conn),
                    "menu": self.menu_payload(conn, btype),
                    "suppliers": rows(conn.execute("SELECT * FROM suppliers WHERE active = 1 ORDER BY name")),
                    "tables": tables,
                    "alerts": {
                        "expiry": expiry_alerts,
                        "low_stock": low_stock_alerts,
                    }
                })
            elif path == "/api/settings":
                settings = get_settings(conn)
                btype = settings.get("business_type", "bar")
                profile = PROFILES.get(btype, PROFILES["retail"])
                self.send_json({
                    "settings": settings,
                    "profile": profile,
                    "profiles": PROFILES,
                    "capabilities": profile["capabilities"],
                })
            elif path == "/api/tables":
                self.send_json(self.tables_payload(conn))
            elif path == "/api/product/image-search":
                q = query.get("q", [""])[0].strip()
                res = search_product_images(q, limit=1)
                self.send_json({"query": q, "results": res, "images": res})
            elif path == "/api/menu":
                settings = get_settings(conn)
                self.send_json(self.menu_payload(conn, settings.get("business_type")))
            elif path == "/api/suppliers":
                self.send_json(rows(conn.execute("SELECT * FROM suppliers ORDER BY name")))
            elif path == "/api/supplier/detail":
                supplier_id = int(query.get("id", [0])[0])
                supplier = dict(conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone())
                products = rows(conn.execute(
                    """
                    SELECT m.name, m.cost_cents, m.stock_qty, MAX(sp.date_received) as last_delivery
                    FROM menu_items m
                    LEFT JOIN stock_purchases sp ON sp.product_id = m.id
                    WHERE m.supplier_id = ? AND m.active = 1
                    GROUP BY m.id
                    """, (supplier_id,)
                ))
                stats = dict(conn.execute(
                    "SELECT COALESCE(SUM(total_cost_cents), 0) as total_purchases FROM stock_purchases WHERE supplier_id = ?",
                    (supplier_id,)
                ).fetchone())
                supplier["products"] = products
                supplier["total_purchases"] = stats["total_purchases"]
                self.send_json(supplier)
            elif path == "/api/stock":
                self.send_json(rows(conn.execute(
                    """
                    SELECT id, name, sku, barcode, stock_qty, unit, category_id, price_cents, cost_cents,
                           wholesale_price_cents, reorder_level, batch_no, expiry_date, manufacturer, strength,
                           variants_json, decimal_qty_enabled, image_url
                    FROM menu_items WHERE active = 1 ORDER BY stock_qty ASC, name
                    """
                )))
            elif path == "/api/order":
                order_id = query.get("id", [""])[0]
                if not order_id.isdigit():
                    return self.send_json({"error": "invalid_id"}, 400)
                order = get_order_payload(conn, int(order_id))
                if not order:
                    return self.send_json({"error": "not_found"}, 404)
                self.send_json(order)
            elif path == "/api/orders":
                status = query.get("status", ["open"])[0]
                sql = """
                    SELECT o.*, u.full_name AS employee_name
                    FROM orders o
                    LEFT JOIN users u ON u.id = o.created_by
                    WHERE (? = 'all' OR o.status = ?)
                    ORDER BY o.updated_at DESC LIMIT 80
                """
                self.send_json(rows(conn.execute(sql, (status, status))))
            elif path == "/api/payments":
                if not self.require_cashier(user):
                    return
                term = query.get("q", [""])[0].strip()
                like = f"%{term}%"
                self.send_json(rows(conn.execute(
                    """
                    SELECT o.*, u.full_name AS employee_name
                    FROM orders o
                    LEFT JOIN users u ON u.id = o.created_by
                    WHERE o.status IN ('open', 'sent')
                    AND (? = '' OR o.ticket_no LIKE ? OR u.full_name LIKE ? OR o.customer_name LIKE ?)
                    ORDER BY o.updated_at DESC LIMIT 80
                    """,
                    (term, like, like, like),
                )))
            elif path == "/api/reports":
                period = query.get("period", ["today"])[0]
                # Determine timestamp threshold based on period
                ts = now()
                if period == "today":
                    # Simple assumption: last 24h for today
                    threshold = ts - 86400
                elif period == "yesterday":
                    threshold = ts - (86400 * 2)
                    ts = ts - 86400
                elif period == "week":
                    threshold = ts - (86400 * 7)
                elif period == "month":
                    threshold = ts - (86400 * 30)
                else:
                    threshold = ts - 86400
                    
                # Using a single query to get total sales and approximate costs
                totals = dict(conn.execute(
                    """
                    SELECT 
                        COUNT(DISTINCT o.id) AS orders, 
                        COALESCE(SUM(oi.line_total_cents),0) AS sales,
                        COALESCE(SUM(oi.qty * mi.cost_cents),0) AS costs
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE o.status = 'paid' AND o.updated_at >= ? AND o.updated_at <= ?
                    """,
                    (threshold, ts),
                ).fetchone())
                
                # Payment Breakdown
                payments = rows(conn.execute(
                    """
                    SELECT COALESCE(payment_method, 'cash') as method, SUM(total_cents) as amount
                    FROM orders 
                    WHERE status = 'paid' AND updated_at >= ? AND updated_at <= ?
                    GROUP BY payment_method
                    """,
                    (threshold, ts),
                ))
                
                # Top Items
                top_items = rows(conn.execute(
                    """
                    SELECT 
                        oi.name, 
                        SUM(oi.qty) AS qty, 
                        SUM(oi.line_total_cents) AS sales,
                        MAX(mi.stock_qty) as current_stock
                    FROM order_items oi 
                    JOIN orders o ON o.id = oi.order_id
                    LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE o.status = 'paid' AND o.updated_at >= ? AND o.updated_at <= ?
                    GROUP BY oi.name ORDER BY sales DESC LIMIT 15
                    """,
                    (threshold, ts),
                ))
                
                stock_stats = dict(conn.execute(
                    """
                    SELECT 
                        COALESCE(SUM(stock_qty * cost_cents), 0) as inventory_value,
                        COALESCE(SUM(stock_qty * (price_cents - cost_cents)), 0) as potential_profit
                    FROM menu_items 
                    WHERE active = 1 AND stock_qty > 0
                    """
                ).fetchone())
                
                self.send_json({"totals": totals, "payments": payments, "top_items": top_items, "period": period, "stock": stock_stats})
            elif path == "/api/admin/summary":
                if not self.require_manager(user):
                    return
                self.send_json(self.admin_summary(conn))
            elif path == "/api/admin/customers":
                self.send_json(rows(conn.execute("SELECT * FROM customers ORDER BY name")))
            elif path == "/api/admin/users":
                if not self.require_manager(user):
                    return
                self.send_json(rows(conn.execute(
                    "SELECT id, username, full_name, role, active FROM users ORDER BY role, full_name"
                )))
            elif path == "/api/admin/suppliers":
                if not self.require_manager(user):
                    return
                self.send_json(rows(conn.execute("SELECT * FROM suppliers ORDER BY name")))
            else:
                self.send_json({"error": "not_found"}, 404)

    def api_post(self, path, data, user, method="POST", query=None):
        with db() as conn:
            if path == "/api/settings":
                save_settings(conn, data)
                CACHE.clear()
                settings = get_settings(conn)
                btype = settings.get("business_type", "bar")
                profile = PROFILES.get(btype, PROFILES["retail"])
                self.send_json({
                    "ok": True,
                    "settings": settings,
                    "profile": profile,
                    "capabilities": profile["capabilities"],
                })
            elif path == "/api/seed-samples":
                pid = data.get("profile_id")
                seed_sample_data(conn, pid)
                CACHE.clear()
                settings = get_settings(conn)
                self.send_json({"ok": True, "menu": self.menu_payload(conn, settings.get("business_type"))})
            elif path == "/api/product/save-image":
                img_src = data.get("image_url") or data.get("image_base64")
                if not img_src:
                    return self.send_json({"error": "missing_image_data"}, 400)
                saved_url = optimize_and_save_image(img_src)
                if not saved_url:
                    return self.send_json({"error": "image_optimization_failed"}, 400)
                self.send_json({"ok": True, "image_url": saved_url, "local_url": saved_url})
            elif path == "/api/order/kot":
                order_id = int(data["order_id"])
                conn.execute("UPDATE orders SET status = 'sent', updated_at = ? WHERE id = ?", (now(), order_id))
                self.send_json(get_order_payload(conn, order_id))
            elif path == "/api/order/convert-quote":
                order_id = int(data["order_id"])
                conn.execute("UPDATE orders SET is_quote = 0, status = 'open', updated_at = ? WHERE id = ?", (now(), order_id))
                recalc_order(conn, order_id)
                self.send_json(get_order_payload(conn, order_id))
            elif path == "/api/orders":
                employee_id = data.get("employee_id") or user["id"]
                valid_employee = conn.execute(
                    "SELECT id FROM users WHERE id = ? AND role IN ('staff', 'cashier', 'manager', 'terminal') AND active = 1",
                    (int(employee_id),),
                ).fetchone()
                if not valid_employee:
                    employee_id = user["id"]
                ticket = next_ticket(conn)
                customer_name = data.get("customer_name", "") or ""
                table_id = int(data["table_id"]) if data.get("table_id") else None
                notes = data.get("notes", "") or ""
                pricing_tier = data.get("pricing_tier", "retail")
                is_quote = 1 if (data.get("is_quote") or data.get("order_type") == "quote") else 0
                cur = conn.execute(
                    """
                    INSERT INTO orders(ticket_no, table_id, order_type, customer_name, notes, pricing_tier, is_quote, created_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (ticket, table_id, data.get("order_type", "walk-in"), customer_name, notes, pricing_tier, is_quote, employee_id, now(), now()),
                )
                self.send_json(get_order_payload(conn, cur.lastrowid))
            elif path == "/api/order/add":
                order_id = int(data["order_id"])
                item = conn.execute("SELECT * FROM menu_items WHERE id = ? AND active = 1", (int(data["menu_item_id"]),)).fetchone()
                if not item:
                    return self.send_json({"error": "item_not_found"}, 404)
                order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
                if not order:
                    return self.send_json({"error": "order_not_found"}, 404)

                qty = float(data.get("qty", 1))
                note = data.get("note", "").strip()
                variant_info = data.get("variant_info", "").strip()
                batch_no = data.get("batch_no", "") or (item["batch_no"] or "")

                pricing_tier = data.get("pricing_tier") or order["pricing_tier"] or "retail"
                if pricing_tier == "wholesale" and item["wholesale_price_cents"] > 0:
                    unit_price = item["wholesale_price_cents"]
                elif data.get("unit_price_cents"):
                    unit_price = int(data["unit_price_cents"])
                else:
                    unit_price = item["price_cents"]

                existing = conn.execute(
                    "SELECT * FROM order_items WHERE order_id = ? AND menu_item_id = ? AND note = ? AND variant_info = ?",
                    (order_id, item["id"], note, variant_info),
                ).fetchone()
                if existing:
                    new_qty = existing["qty"] + qty
                    conn.execute(
                        "UPDATE order_items SET qty = ?, line_total_cents = ? WHERE id = ?",
                        (new_qty, int(round(new_qty * unit_price)), existing["id"]),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO order_items(order_id, menu_item_id, name, qty, unit_price_cents, line_total_cents, note, variant_info, batch_no)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (order_id, item["id"], item["name"], qty, unit_price, int(round(qty * unit_price)), note, variant_info, batch_no),
                    )
                recalc_order(conn, order_id)
                self.send_json(get_order_payload(conn, order_id))
            elif path == "/api/order/qty":
                item_id = int(data["item_id"])
                qty = max(0.0, float(data["qty"]))
                row = conn.execute("SELECT order_id, unit_price_cents FROM order_items WHERE id = ?", (item_id,)).fetchone()
                if not row:
                    return self.send_json({"error": "item_not_found"}, 404)
                if qty <= 0:
                    conn.execute("DELETE FROM order_items WHERE id = ?", (item_id,))
                else:
                    conn.execute(
                        "UPDATE order_items SET qty = ?, line_total_cents = ? WHERE id = ?",
                        (qty, int(round(qty * row["unit_price_cents"])), item_id),
                    )
                recalc_order(conn, row["order_id"])
                self.send_json(get_order_payload(conn, row["order_id"]))
            elif path == "/api/order/pay":
                order_id = int(data["order_id"])
                order = conn.execute("SELECT status, total_cents, customer_name FROM orders WHERE id = ?", (order_id,)).fetchone()
                if not order:
                    return self.send_json({"error": "order_not_found"}, 404)
                
                if order["status"] != "paid":
                    items = conn.execute("SELECT menu_item_id, qty FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
                    for item in items:
                        if item["menu_item_id"]:
                            conn.execute("UPDATE menu_items SET stock_qty = stock_qty - ? WHERE id = ?", (item["qty"], item["menu_item_id"]))
                            conn.execute(
                                "INSERT INTO stock_movements(product_id, qty_change, reason, note, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                                (item["menu_item_id"], -item["qty"], "sale", f"Order #{order_id}", user["id"], now()),
                            )

                payment_method = data.get("payment_method", "cash")
                payment_ref = data.get("payment_ref", "").strip()
                customer_name = order["customer_name"]

                if payment_method == "mpesa" and payment_ref:
                    import urllib.request, urllib.error
                    
                    phone_no = payment_ref
                    if phone_no.startswith('0'):
                        phone_no = '+254' + phone_no[1:]
                    
                    # paystack_payload = json.dumps({
                    #     "email": f"customer_{order_id}@eityfit.com",
                    #     "amount": order["total_cents"],
                    #     "currency": "KES",
                    #     "mobile_money": {
                    #         "phone": phone_no,
                    #         "provider": "mpesa"
                    #     }
                    # }).encode('utf-8')
                    # 
                    # req = urllib.request.Request("https://api.paystack.co/charge", data=paystack_payload)
                    # req.add_header("Authorization", "Bearer " + __import__("os").environ.get("PAYSTACK_SECRET_KEY", "your_paystack_secret_key_here"))
                    # req.add_header("Content-Type", "application/json")
                    # req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
                    # 
                    # try:
                    #     with urllib.request.urlopen(req) as response:
                    #         res_data = json.loads(response.read().decode())
                    #         if not res_data.get("status"):
                    #             return self.send_json({"error": res_data.get("message", "Paystack STK push failed")}, 400)
                    # except urllib.error.HTTPError as e:
                    #     try:
                    #         err_res = json.loads(e.read().decode())
                    #         err_msg = err_res.get("message", "Payment API error")
                    #     except:
                    #         err_msg = str(e)
                    #     return self.send_json({"error": err_msg}, 400)
                    # except Exception as e:
                    #     return self.send_json({"error": "Connection to Paystack failed: " + str(e)}, 500)

                    # Auto-save customer
                    customer = conn.execute("SELECT id, name FROM customers WHERE phone = ?", (payment_ref,)).fetchone()
                    if not customer:
                        conn.execute("INSERT INTO customers(name, phone, notes) VALUES ('Temp', ?, 'Auto-saved from M-Pesa purchase')", (payment_ref,))
                        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        new_name = f"Customer {new_id}"
                        conn.execute("UPDATE customers SET name = ? WHERE id = ?", (new_name, new_id))
                        if not customer_name:
                            customer_name = new_name
                    else:
                        if not customer_name:
                            customer_name = customer["name"]

                conn.execute(
                    "UPDATE orders SET status = 'paid', paid_cents = ?, payment_method = ?, payment_ref = ?, customer_name = ?, updated_at = ? WHERE id = ?",
                    (order["total_cents"], payment_method, payment_ref, customer_name, now(), order_id),
                )
                self.send_json(get_order_payload(conn, order_id))
            elif path == "/api/order/status":
                order_id = int(data["order_id"])
                status = data.get("status", "sent")
                conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", (status, now(), order_id))
                self.send_json(get_order_payload(conn, order_id))
            elif path == "/api/menu/item" and method == "DELETE":
                item_id = int(query.get("id", [0])[0])
                try:
                    conn.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
                    CACHE["menu"] = None
                    self.send_json(self.menu_payload(conn))
                except sqlite3.IntegrityError:
                    self.send_json({"error": "Cannot delete product. It has already been sold on past receipts or has stock history."}, status=400)
            elif path == "/api/menu/item":
                price_cents = int(float(data.get("price", "0")) * 100)
                cost_cents = int(float(data.get("cost", "0")) * 100)
                wholesale_price_cents = int(float(data.get("wholesale_price", "0")) * 100) if data.get("wholesale_price") else 0
                sku = data.get("sku", "").strip() or None
                barcode = data.get("barcode", "").strip() or None
                unit = data.get("unit", "pcs").strip() or "pcs"
                stock_qty = float(data.get("stock_qty", 0))
                reorder_level = int(data.get("reorder_level", 5))
                batch_no = data.get("batch_no", "").strip() or None
                expiry_date = data.get("expiry_date", "").strip() or None
                manufacturer = data.get("manufacturer", "").strip() or None
                strength = data.get("strength", "").strip() or None
                variants_json = data.get("variants_json", "").strip() or ""
                decimal_qty_enabled = 1 if data.get("decimal_qty_enabled") in (1, "1", True, "true") else 0

                image_url = data.get("image_url")
                if data.get("image_base64"):
                    saved = optimize_and_save_image(data["image_base64"])
                    if saved:
                        image_url = saved

                if data.get("id"):
                    conn.execute(
                        """
                        UPDATE menu_items SET category_id=?, name=?, price_cents=?, cost_cents=?, color=?, active=?,
                               sku=?, barcode=?, unit=?, stock_qty=?, image_url=?, reorder_level=?,
                               batch_no=?, expiry_date=?, manufacturer=?, strength=?,
                               wholesale_price_cents=?, variants_json=?, decimal_qty_enabled=?
                        WHERE id=?
                        """,
                        (
                            int(data["category_id"]), data["name"], price_cents, cost_cents,
                            data.get("color", "#334155"), int(data.get("active", 1)),
                            sku, barcode, unit, stock_qty, image_url, reorder_level,
                            batch_no, expiry_date, manufacturer, strength,
                            wholesale_price_cents, variants_json, decimal_qty_enabled,
                            int(data["id"])
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO menu_items(
                            category_id, name, price_cents, cost_cents, color, sku, barcode, unit, stock_qty, image_url,
                            reorder_level, batch_no, expiry_date, manufacturer, strength, wholesale_price_cents,
                            variants_json, decimal_qty_enabled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            int(data["category_id"]), data["name"], price_cents, cost_cents, data.get("color", "#334155"),
                            sku, barcode, unit, stock_qty, image_url, reorder_level, batch_no, expiry_date,
                            manufacturer, strength, wholesale_price_cents, variants_json, decimal_qty_enabled
                        ),
                    )
                CACHE.clear()
                settings = get_settings(conn)
                self.send_json(self.menu_payload(conn, settings.get("business_type")))
            elif path == "/api/admin/user":
                if not self.require_manager(user):
                    return
                username = data.get("username", "").strip()
                full_name = data.get("full_name", "").strip()
                role = data.get("role", "staff")
                active = int(data.get("active", 1))
                password = data.get("password", "").strip()
                if role not in ("staff", "cashier", "manager"):
                    return self.send_json({"error": "bad_role"}, 400)
                if not username or not full_name:
                    return self.send_json({"error": "missing_user_fields"}, 400)
                if data.get("id"):
                    user_id = int(data["id"])
                    if password:
                        conn.execute(
                            "UPDATE users SET username=?, full_name=?, role=?, active=?, password_hash=? WHERE id=?",
                            (username, full_name, role, active, hash_password(password), user_id),
                        )
                    else:
                        conn.execute(
                            "UPDATE users SET username=?, full_name=?, role=?, active=? WHERE id=?",
                            (username, full_name, role, active, user_id),
                        )
                else:
                    if not password:
                        password = "1234" if role == "staff" else "admin123"
                    conn.execute(
                        "INSERT INTO users(username, full_name, role, active, password_hash) VALUES (?, ?, ?, ?, ?)",
                        (username, full_name, role, active, hash_password(password)),
                    )
                self.send_json(rows(conn.execute(
                    "SELECT id, username, full_name, role, active FROM users ORDER BY role, full_name"
                )))
            elif path == "/api/purchase":
                supplier_id = int(data["supplier_id"])
                product_id = int(data["product_id"])
                qty = int(data["qty"])
                cost = int(data["cost_cents"])
                total = qty * cost
                conn.execute("UPDATE menu_items SET cost_cents = ?, stock_qty = stock_qty + ?, supplier_id = ? WHERE id = ?", (cost, qty, supplier_id, product_id))
                conn.execute(
                    "INSERT INTO stock_purchases (supplier_id, product_id, qty_received, cost_per_unit_cents, total_cost_cents, date_received, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (supplier_id, product_id, qty, cost, total, now(), user["id"])
                )
                conn.execute(
                    "INSERT INTO stock_movements (product_id, qty_change, reason, note, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (product_id, qty, 'purchase', f'Supplier {supplier_id}', user["id"], now())
                )
                self.send_json({"success": True})
            elif path == "/api/admin/supplier":
                name = data.get("name", "").strip()
                phone = data.get("phone", "").strip()
                email = data.get("email", "").strip()
                address = data.get("address", "").strip()
                active = int(data.get("active", 1))
                if not name:
                    return self.send_json({"error": "missing_supplier_name"}, 400)
                if data.get("id"):
                    conn.execute(
                        "UPDATE suppliers SET name=?, phone=?, email=?, address=?, active=? WHERE id=?",
                        (name, phone, email, address, active, int(data["id"])),
                    )
                else:
                    conn.execute(
                        "INSERT INTO suppliers(name, phone, email, address, active) VALUES (?, ?, ?, ?, ?)",
                        (name, phone, email, address, active),
                    )
                self.send_json(rows(conn.execute("SELECT * FROM suppliers ORDER BY name")))
            elif path == "/api/admin/customer":
                name = data.get("name", "").strip()
                phone = data.get("phone", "").strip()
                email = data.get("email", "").strip()
                notes = data.get("notes", "").strip()
                if not name:
                    return self.send_json({"error": "missing_customer_name"}, 400)
                if data.get("id"):
                    conn.execute(
                        "UPDATE customers SET name=?, phone=?, email=?, notes=? WHERE id=?",
                        (name, phone, email, notes, int(data["id"])),
                    )
                else:
                    conn.execute(
                        "INSERT INTO customers(name, phone, email, notes) VALUES (?, ?, ?, ?)",
                        (name, phone, email, notes),
                    )
                self.send_json(rows(conn.execute("SELECT * FROM customers ORDER BY name")))
            elif path == "/api/stock/adjust":
                if not self.require_manager(user):
                    return
                product_id = int(data["product_id"])
                qty_change = int(data["qty_change"])
                reason = data.get("reason", "adjustment")
                note = data.get("note", "")
                conn.execute(
                    "UPDATE menu_items SET stock_qty = stock_qty + ? WHERE id = ?",
                    (qty_change, product_id),
                )
                conn.execute(
                    "INSERT INTO stock_movements(product_id, qty_change, reason, note, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (product_id, qty_change, reason, note, user["id"], now()),
                )
                CACHE["menu"] = None
                self.send_json({"ok": True, "product_id": product_id, "qty_change": qty_change})
            else:
                self.send_json({"error": "not_found"}, 404)

    def menu_payload(self, conn, business_type=None):
        if not business_type:
            settings = get_settings(conn)
            business_type = settings.get("business_type")

        cache_key = f"menu_{business_type}"
        if CACHE.get(cache_key) and now() - CACHE.get(f"menu_ts_{business_type}", 0) < 15:
            return CACHE[cache_key]

        has_profile_cats = conn.execute(
            "SELECT COUNT(*) FROM categories WHERE business_type = ?", (business_type,)
        ).fetchone()[0]

        if has_profile_cats > 0:
            categories = rows(conn.execute(
                "SELECT * FROM categories WHERE business_type = ? OR business_type IS NULL OR business_type = 'all' ORDER BY sort_order, name",
                (business_type,)
            ))
            cat_ids = [c["id"] for c in categories]
            placeholders = ",".join("?" * len(cat_ids))
            items = rows(conn.execute(
                f"SELECT * FROM menu_items WHERE active = 1 AND category_id IN ({placeholders}) ORDER BY category_id, name",
                cat_ids,
            ))
        else:
            categories = rows(conn.execute("SELECT * FROM categories ORDER BY sort_order, name"))
            items = rows(conn.execute("SELECT * FROM menu_items WHERE active = 1 ORDER BY category_id, name"))

        payload = {"categories": categories, "items": items}
        CACHE[cache_key] = payload
        CACHE[f"menu_ts_{business_type}"] = now()
        return payload

    def tables_payload(self, conn):
        return rows(conn.execute(
            """
            SELECT t.*, o.id AS order_id, o.ticket_no, o.total_cents
            FROM dining_tables t
            LEFT JOIN orders o ON o.table_id = t.id AND o.status IN ('open', 'sent')
            WHERE t.active = 1 ORDER BY t.id
            """
        ))

    def employees_payload(self, conn):
        return rows(conn.execute(
            """
            SELECT MIN(id) AS id, full_name AS name
            FROM users
            WHERE role IN ('staff', 'cashier', 'manager') AND active = 1
            GROUP BY full_name
            ORDER BY full_name
            """
        ))

    def admin_summary(self, conn):
        day_start = now() - 86400
        week_start = now() - 604800
        totals = dict(conn.execute(
            """
            SELECT
              COUNT(CASE WHEN status = 'paid' AND updated_at >= ? THEN 1 END) AS paid_today,
              COALESCE(SUM(CASE WHEN status = 'paid' AND updated_at >= ? THEN total_cents END), 0) AS sales_today,
              COUNT(CASE WHEN status IN ('open','sent') THEN 1 END) AS unpaid_orders,
              COALESCE(SUM(CASE WHEN status IN ('open','sent') THEN total_cents END), 0) AS unpaid_total,
              COALESCE(SUM(CASE WHEN status = 'paid' AND updated_at >= ? THEN total_cents END), 0) AS sales_week
            FROM orders
            """,
            (day_start, day_start, week_start),
        ).fetchone())
        by_employee = rows(conn.execute(
            """
            SELECT u.full_name AS employee, COUNT(o.id) AS orders, COALESCE(SUM(o.total_cents), 0) AS sales
            FROM orders o JOIN users u ON u.id = o.created_by
            WHERE o.status = 'paid' AND o.updated_at >= ?
            GROUP BY u.id, u.full_name
            ORDER BY sales DESC LIMIT 8
            """,
            (week_start,),
        ))
        by_method = rows(conn.execute(
            """
            SELECT COALESCE(payment_method, 'unknown') AS method, COUNT(*) AS count, COALESCE(SUM(total_cents), 0) AS sales
            FROM orders
            WHERE status = 'paid' AND updated_at >= ?
            GROUP BY payment_method ORDER BY sales DESC
            """,
            (week_start,),
        ))
        top_items = rows(conn.execute(
            """
            SELECT oi.name, SUM(oi.qty) AS qty, SUM(oi.line_total_cents) AS sales
            FROM order_items oi JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'paid' AND o.updated_at >= ?
            GROUP BY oi.name ORDER BY sales DESC LIMIT 8
            """,
            (week_start,),
        ))
        counts = dict(conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM users WHERE active = 1 AND role NOT IN ('terminal')) AS active_users,
              (SELECT COUNT(*) FROM menu_items WHERE active = 1) AS active_items,
              (SELECT COUNT(*) FROM suppliers WHERE active = 1) AS active_suppliers
            """
        ).fetchone())
        sales_trend = rows(conn.execute(
            """
            SELECT strftime('%Y-%m-%d', updated_at, 'unixepoch', 'localtime') AS day, COALESCE(SUM(total_cents), 0) AS sales
            FROM orders
            WHERE status = 'paid' AND updated_at >= ?
            GROUP BY day ORDER BY day ASC
            """,
            (week_start,)
        ))
        return {
            "totals": totals,
            "counts": counts,
            "by_employee": by_employee,
            "by_method": by_method,
            "top_items": top_items,
            "sales_trend": sales_trend,
        }

    do_DELETE = do_POST

if __name__ == "__main__":
    init_db()
    print(f"{STORE_NAME} Bar POS running at http://{HOST}:{PORT}")
    print("Staff PIN login: 1234 | Admin login: admin / admin123")

    class ReuseServer(ThreadingHTTPServer):
        allow_reuse_address = True

    ReuseServer((HOST, PORT), POSHandler).serve_forever()
