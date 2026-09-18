from pathlib import Path
import re

p = Path('app.py')
a = Path('static/admin.js')
py = p.read_text()
adm = a.read_text()

# ── Helpers: business workspace follows the authenticated session ─────────────
old_find = '''def find_customer_by_phone(conn, value):
    target = normalize_customer_phone(value)
    if not target:
        return None
    for row in conn.execute("SELECT id, name, phone FROM customers").fetchall():
        if normalize_customer_phone(row['phone']) == target:
            return row
    return None
'''
new_find = '''def active_business_type(user=None, conn=None):
    btype = (user or {}).get("business_type") if user else None
    if btype in PROFILES:
        return btype
    if conn is not None:
        settings = get_settings(conn)
        btype = settings.get("business_type")
        if btype in PROFILES:
            return btype
    return "retail"


def scoped_settings(conn, business_type):
    business_type = business_type if business_type in PROFILES else "retail"
    settings = dict(get_settings(conn))
    profile = PROFILES[business_type]
    # The global settings table is still used for common settings, but a session
    # must always display the category/workspace it actually logged into.
    if settings.get("business_type") != business_type:
        settings["business_name"] = profile["name"]
        settings["business_tagline"] = profile["tagline"]
    settings["business_type"] = business_type
    return settings


def find_customer_by_phone(conn, value, business_type=None):
    target = normalize_customer_phone(value)
    if not target:
        return None
    if business_type in PROFILES:
        source = conn.execute(
            "SELECT id, name, phone FROM customers WHERE business_type = ?",
            (business_type,),
        ).fetchall()
    else:
        source = conn.execute("SELECT id, name, phone FROM customers").fetchall()
    for row in source:
        if normalize_customer_phone(row['phone']) == target:
            return row
    return None
'''
if old_find in py:
    py = py.replace(old_find, new_find, 1)
elif 'def active_business_type(' not in py:
    raise SystemExit('Could not patch customer/workspace helpers')

# ── DB migration: business_type on operational data ───────────────────────────
migration_marker = '        # Seed sample data for profiles\n'
migration = '''        # Business workspace isolation. One codebase, separate operational data per shop category.
        workspace_migrations = [
            ("orders", "business_type", "ALTER TABLE orders ADD COLUMN business_type TEXT NOT NULL DEFAULT 'bar'"),
            ("customers", "business_type", "ALTER TABLE customers ADD COLUMN business_type TEXT NOT NULL DEFAULT 'bar'"),
            ("suppliers", "business_type", "ALTER TABLE suppliers ADD COLUMN business_type TEXT NOT NULL DEFAULT 'bar'"),
            ("stock_purchases", "business_type", "ALTER TABLE stock_purchases ADD COLUMN business_type TEXT NOT NULL DEFAULT 'bar'"),
            ("stock_movements", "business_type", "ALTER TABLE stock_movements ADD COLUMN business_type TEXT NOT NULL DEFAULT 'bar'"),
        ]
        for table_name, col_name, sql in workspace_migrations:
            table_cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}
            if col_name not in table_cols:
                conn.execute(sql)

        # Recover the correct shop category for historical sales by looking at
        # the category of the products that were actually sold on each order.
        conn.execute("""
            UPDATE orders
               SET business_type = COALESCE((
                   SELECT c.business_type
                     FROM order_items oi
                     JOIN menu_items mi ON mi.id = oi.menu_item_id
                     JOIN categories c ON c.id = mi.category_id
                    WHERE oi.order_id = orders.id
                      AND c.business_type IN ('retail','pharmacy','restaurant','hardware','boutique','bar')
                    ORDER BY oi.id
                    LIMIT 1
               ), business_type)
        """)

        # Existing suppliers/purchases/movements can also be inferred from their products.
        conn.execute("""
            UPDATE suppliers
               SET business_type = COALESCE((
                   SELECT c.business_type
                     FROM menu_items mi
                     JOIN categories c ON c.id = mi.category_id
                    WHERE mi.supplier_id = suppliers.id
                      AND c.business_type IN ('retail','pharmacy','restaurant','hardware','boutique','bar')
                    LIMIT 1
               ), business_type)
        """)
        conn.execute("""
            UPDATE stock_purchases
               SET business_type = COALESCE((
                   SELECT c.business_type
                     FROM menu_items mi JOIN categories c ON c.id = mi.category_id
                    WHERE mi.id = stock_purchases.product_id
                    LIMIT 1
               ), business_type)
        """)
        conn.execute("""
            UPDATE stock_movements
               SET business_type = COALESCE((
                   SELECT c.business_type
                     FROM menu_items mi JOIN categories c ON c.id = mi.category_id
                    WHERE mi.id = stock_movements.product_id
                    LIMIT 1
               ), business_type)
        """)

        # Best-effort recovery of historical customer workspace from matching sales.
        for customer_row in conn.execute("SELECT id, name, phone FROM customers").fetchall():
            cust_phone = normalize_customer_phone(customer_row["phone"])
            matches = conn.execute(
                "SELECT business_type, payment_ref, customer_name FROM orders ORDER BY updated_at DESC"
            ).fetchall()
            for order_row in matches:
                same_phone = cust_phone and normalize_customer_phone(order_row["payment_ref"]) == cust_phone
                same_name = customer_row["name"] and order_row["customer_name"] == customer_row["name"]
                if same_phone or same_name:
                    conn.execute(
                        "UPDATE customers SET business_type = ? WHERE id = ?",
                        (order_row["business_type"], customer_row["id"]),
                    )
                    break

'''
if 'workspace_migrations = [' not in py:
    if migration_marker not in py:
        raise SystemExit('DB migration marker missing')
    py = py.replace(migration_marker, migration + migration_marker, 1)

# ── Admin login: explicit shop category selector ───────────────────────────────
admin_start = py.index('def admin_login_page(')
admin_end = py.index('\n\nclass POSHandler', admin_start)
new_admin_login = '''def admin_login_page(error="", selected_business_type=None):
    if selected_business_type not in PROFILES:
        with db() as conn:
            selected_business_type = active_business_type(None, conn)
    profile = PROFILES[selected_business_type]
    options = "".join(
        f'<option value="{key}" {"selected" if key == selected_business_type else ""}>{item["icon"]} {item["name"]}</option>'
        for key, item in PROFILES.items()
    )
    message = f'<p class="err">{error}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{profile['name']} — Admin Login</title>
  <link rel="stylesheet" href="/static/admin.css?v={int(time.time())}">
  <style>
    body {{ display:grid; place-items:center; min-height:100vh; background:var(--bg); }}
    .admin-login-panel {{ width:min(410px,calc(100vw - 32px)); background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow-lg); padding:36px; display:grid; gap:18px; }}
    .admin-login-panel .brand {{ display:flex; align-items:center; gap:10px; }}
    .admin-login-panel .logo-icon {{ width:42px; height:42px; background:var(--primary); border-radius:9px; display:grid; place-items:center; font-size:22px; color:#fff; }}
    .admin-login-panel h2 {{ margin:0; font-size:20px; font-weight:800; color:var(--navy); }}
    .admin-login-panel p {{ margin:2px 0 0; color:var(--muted); font-size:13px; }}
    .admin-login-panel .err {{ color:var(--danger); font-weight:700; font-size:13px; }}
    .workspace-box {{ padding:12px; border:1px solid var(--line); background:var(--bg); border-radius:10px; }}
  </style>
</head>
<body>
  <form class="admin-login-panel" method="post" action="/admin">
    <div class="brand">
      <div class="logo-icon">{profile['icon']}</div>
      <div><h2>Shop Admin Portal</h2><p>Choose the shop workspace you want to manage.</p></div>
    </div>
    {message}
    <div class="workspace-box">
      <label class="form-label">Shop Category / Workspace</label>
      <select class="form-select" name="business_type" required>{options}</select>
    </div>
    <div class="form-group"><label class="form-label">Username</label><input class="form-input" name="username" autocomplete="username" autofocus placeholder="admin"></div>
    <div class="form-group"><label class="form-label">Password</label><input class="form-input" name="password" type="password" autocomplete="current-password" placeholder="••••••••"></div>
    <button class="btn btn-primary" type="submit" style="width:100%;justify-content:center;padding:12px">Sign In to Selected Shop</button>
  </form>
</body>
</html>"""
'''
py = py[:admin_start] + new_admin_login + py[admin_end:]

# ── Admin page server-rendered branding so it is obvious before JS runs ───────
if 'def hidden_admin_page():' in py:
    start = py.index('def hidden_admin_page():')
    end = py.index('\n\ndef page(', start)
    block = py[start:end]
    block = block.replace(
        'def hidden_admin_page():\n    return """',
        'def hidden_admin_page(business_type="retail"):\n    profile = PROFILES.get(business_type, PROFILES["retail"])\n    html = """',
        1,
    )
    block = block.replace('<title>Admin Portal — EITY FIT</title>', '<title>__SHOP_NAME__ — Admin Portal</title>', 1)
    block = block.replace('<div class="logo-icon" id="adminBusinessIcon">🛒</div>', '<div class="logo-icon" id="adminBusinessIcon">__SHOP_ICON__</div>', 1)
    block = block.replace('<span class="name" id="adminBusinessName">POS</span>', '<span class="name" id="adminBusinessName">__SHOP_NAME__</span>', 1)
    block = block.replace('<div class="tag" id="adminPortalTag">Admin Portal</div>', '<div class="tag" id="adminPortalTag">__SHOP_NAME__ Admin</div>', 1)
    if not block.endswith('"""'):
        raise SystemExit('Unexpected hidden_admin_page ending')
    block = block[:-3] + '''"""
    return (html
            .replace("__SHOP_ICON__", profile.get("icon", "🏪"))
            .replace("__SHOP_NAME__", profile.get("name", business_type)))'''
    py = py[:start] + block + py[end:]

# ── Session: lock each login to a specific business workspace ─────────────────
# Staff login uses the category chosen on the staff login page.
staff_session = 'SESSIONS[sid] = {"id": user["id"], "username": user["username"], "role": user["role"], "name": user["full_name"]}'
first = py.find(staff_session)
if first != -1:
    insert_at = py.rfind('            if user:', 0, first)
    if insert_at != -1 and 'login_business_type = active_business_type' not in py[insert_at:first]:
        marker = '            if user:\n                sid = secrets.token_urlsafe(32)\n'
        repl = '            if user:\n                with db() as login_conn:\n                    login_business_type = active_business_type(None, login_conn)\n                sid = secrets.token_urlsafe(32)\n'
        py = py.replace(marker, repl, 1)
    py = py[:py.find(staff_session)] + staff_session.replace('}', ', "business_type": login_business_type}') + py[py.find(staff_session)+len(staff_session):]

# Cashier login follows current selected workspace.
second = py.find(staff_session)
if second != -1:
    marker = '            if user and check_password(data.get("password", ""), user["password_hash"]):\n                sid = secrets.token_urlsafe(32)\n'
    repl = '            if user and check_password(data.get("password", ""), user["password_hash"]):\n                with db() as login_conn:\n                    login_business_type = active_business_type(None, login_conn)\n                sid = secrets.token_urlsafe(32)\n'
    py = py.replace(marker, repl, 1)
    pos = py.find(staff_session)
    if pos != -1:
        py = py[:pos] + staff_session.replace('}', ', "business_type": login_business_type}') + py[pos+len(staff_session):]

# Admin login explicitly selects its workspace.
admin_session = 'SESSIONS[sid] = {"id": user["id"], "username": user["username"], "role": user["role"], "name": user["full_name"]}'
pos = py.find(admin_session)
if pos != -1:
    marker = '        if path == "/admin":\n            data = self.read_body()\n'
    repl = '''        if path == "/admin":
            data = self.read_body()
            login_business_type = data.get("business_type", "")
            if login_business_type not in PROFILES:
                with db() as login_conn:
                    login_business_type = active_business_type(None, login_conn)
'''
    py = py.replace(marker, repl, 1)
    pos = py.find(admin_session, py.find('        if path == "/admin":'))
    if pos != -1:
        py = py[:pos] + admin_session.replace('}', ', "business_type": login_business_type}') + py[pos+len(admin_session):]

# Admin pages render the selected workspace, not a generic portal.
py = py.replace('self.send_html(hidden_admin_page())', 'self.send_html(hidden_admin_page(active_business_type(user)))')

# Receipt must use settings/branding for the order's own workspace.
old_receipt = '''            with db() as conn:
                order = get_order_payload(conn, int(order_id))
                settings = get_settings(conn)
            if not order:
'''
new_receipt = '''            with db() as conn:
                order = get_order_payload(conn, int(order_id))
                current_btype = active_business_type(user, conn)
                settings = scoped_settings(conn, current_btype)
            if not order or order.get("business_type") != current_btype:
'''
if old_receipt in py:
    py = py.replace(old_receipt, new_receipt, 1)

# ── api_get: all operational reads scoped to session business_type ─────────────
get_start = py.index('    def api_get(')
post_start = py.index('    def api_post(', get_start)
get_block = py[get_start:post_start]
get_block = get_block.replace(
    '        with db() as conn:\n            if path == "/api/bootstrap":\n                settings = get_settings(conn)\n                btype = settings.get("business_type", "bar")\n',
    '        with db() as conn:\n            btype = active_business_type(user, conn)\n            settings = scoped_settings(conn, btype)\n            if path == "/api/bootstrap":\n',
    1,
)
get_block = get_block.replace(
    '            elif path == "/api/settings":\n                settings = get_settings(conn)\n                btype = settings.get("business_type", "bar")\n',
    '            elif path == "/api/settings":\n',
    1,
)
get_block = get_block.replace('self.tables_payload(conn)', 'self.tables_payload(conn, btype)')
get_block = get_block.replace('"suppliers": rows(conn.execute("SELECT * FROM suppliers WHERE active = 1 ORDER BY name")),', '"suppliers": rows(conn.execute("SELECT * FROM suppliers WHERE active = 1 AND business_type = ? ORDER BY name", (btype,))),')
get_block = get_block.replace('settings = get_settings(conn)\n                self.send_json(self.menu_payload(conn, settings.get("business_type")))', 'self.send_json(self.menu_payload(conn, btype))', 1)
get_block = get_block.replace('self.send_json(rows(conn.execute("SELECT * FROM suppliers ORDER BY name")))', 'self.send_json(rows(conn.execute("SELECT * FROM suppliers WHERE business_type = ? ORDER BY name", (btype,))))', 1)
get_block = get_block.replace('supplier = dict(conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone())', 'supplier_row = conn.execute("SELECT * FROM suppliers WHERE id = ? AND business_type = ?", (supplier_id, btype)).fetchone()\n                if not supplier_row:\n                    return self.send_json({"error": "supplier_not_found"}, 404)\n                supplier = dict(supplier_row)', 1)

# Stock list only current shop's product categories.
old_stock = '''                    FROM menu_items WHERE active = 1 ORDER BY stock_qty ASC, name
                    """
                )))'''
new_stock = '''                    FROM menu_items mi
                    JOIN categories c ON c.id = mi.category_id
                    WHERE mi.active = 1 AND c.business_type = ?
                    ORDER BY mi.stock_qty ASC, mi.name
                    """, (btype,)
                )))'''
get_block = get_block.replace(old_stock, new_stock, 1)

# Order detail/list/payment queues.
get_block = get_block.replace('order = get_order_payload(conn, int(order_id))\n                if not order:', 'order = get_order_payload(conn, int(order_id))\n                if not order or order.get("business_type") != btype:', 1)
get_block = get_block.replace("WHERE (? = 'all' OR o.status = ?)", "WHERE o.business_type = ? AND (? = 'all' OR o.status = ?)", 1)
get_block = get_block.replace('rows(conn.execute(sql, (status, status)))', 'rows(conn.execute(sql, (btype, status, status)))', 1)
get_block = get_block.replace("WHERE o.status IN ('open', 'sent')\n                    AND (? = ''", "WHERE o.business_type = ? AND o.status IN ('open', 'sent')\n                    AND (? = ''", 1)
get_block = get_block.replace('(term, like, like, like),', '(btype, term, like, like, like),', 1)

# Reports: add business_type to each order aggregation.
get_block = get_block.replace("WHERE o.status = 'paid' AND o.updated_at >= ? AND o.updated_at <= ?", "WHERE o.business_type = ? AND o.status = 'paid' AND o.updated_at >= ? AND o.updated_at <= ?")
get_block = get_block.replace('(threshold, ts),', '(btype, threshold, ts),')
get_block = get_block.replace("WHERE status = 'paid' AND updated_at >= ? AND updated_at <= ?", "WHERE business_type = ? AND status = 'paid' AND updated_at >= ? AND updated_at <= ?", 1)
# Above args replacement already changed matching tuples globally in report block where present.

# Stock valuation only current profile's items.
get_block = get_block.replace(
    'FROM menu_items \n                    WHERE active = 1 AND stock_qty > 0',
    'FROM menu_items mi JOIN categories c ON c.id = mi.category_id\n                    WHERE mi.active = 1 AND mi.stock_qty > 0 AND c.business_type = ?'
)
get_block = get_block.replace('"""\n                ).fetchone())\n                \n                self.send_json({"totals": totals', '""", (btype,)\n                ).fetchone())\n                \n                self.send_json({"totals": totals', 1)

get_block = get_block.replace('self.send_json(self.admin_summary(conn))', 'self.send_json(self.admin_summary(conn, btype))', 1)
get_block = get_block.replace('self.send_json(rows(conn.execute("SELECT * FROM customers ORDER BY name")))', 'self.send_json(rows(conn.execute("SELECT * FROM customers WHERE business_type = ? ORDER BY name", (btype,))))', 1)
get_block = get_block.replace('self.send_json(rows(conn.execute("SELECT * FROM suppliers ORDER BY name")))', 'self.send_json(rows(conn.execute("SELECT * FROM suppliers WHERE business_type = ? ORDER BY name", (btype,))))')

# Scope expiry/low-stock alerts to profile products.
get_block = get_block.replace(
    "SELECT COUNT(*) FROM menu_items WHERE active = 1 AND expiry_date IS NOT NULL AND expiry_date != '' AND expiry_date <= ?",
    "SELECT COUNT(*) FROM menu_items mi JOIN categories c ON c.id = mi.category_id WHERE mi.active = 1 AND c.business_type = ? AND mi.expiry_date IS NOT NULL AND mi.expiry_date != '' AND mi.expiry_date <= ?",
    1,
)
get_block = get_block.replace('(future_str,)', '(btype, future_str,)', 1)
get_block = get_block.replace(
    '"SELECT COUNT(*) FROM menu_items WHERE active = 1 AND stock_qty <= reorder_level"',
    '"SELECT COUNT(*) FROM menu_items mi JOIN categories c ON c.id = mi.category_id WHERE mi.active = 1 AND c.business_type = ? AND mi.stock_qty <= mi.reorder_level", (btype,)'
)
py = py[:get_start] + get_block + py[post_start:]

# ── api_post: create/update only inside current workspace ──────────────────────
post_start = py.index('    def api_post(')
menu_start = py.index('    def menu_payload(', post_start)
post_block = py[post_start:menu_start]
post_block = post_block.replace('        with db() as conn:\n            if path == "/api/settings":', '        with db() as conn:\n            btype = active_business_type(user, conn)\n            if path == "/api/settings":', 1)
post_block = post_block.replace(
    '            if path == "/api/settings":\n                save_settings(conn, data)\n',
    '            if path == "/api/settings":\n                requested_btype = data.get("business_type")\n                if requested_btype in PROFILES:\n                    btype = requested_btype\n                    user["business_type"] = requested_btype\n                save_settings(conn, data)\n',
    1,
)
post_block = post_block.replace('settings = get_settings(conn)\n                btype = settings.get("business_type", "bar")', 'settings = scoped_settings(conn, btype)', 1)
post_block = post_block.replace('settings = get_settings(conn)\n                self.send_json({"ok": True, "menu": self.menu_payload(conn, settings.get("business_type"))})', 'self.send_json({"ok": True, "menu": self.menu_payload(conn, btype)})', 1)

# Order creation owns the current workspace.
post_block = post_block.replace('ticket = next_ticket(conn)', 'ticket = next_ticket(conn)', 1)
old_insert = '''INSERT INTO orders(ticket_no, table_id, order_type, customer_name, notes, pricing_tier, is_quote, created_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
new_insert = '''INSERT INTO orders(ticket_no, table_id, order_type, customer_name, notes, pricing_tier, is_quote, created_by, created_at, updated_at, business_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
post_block = post_block.replace(old_insert, new_insert, 1)
post_block = post_block.replace('(ticket, table_id, data.get("order_type", "walk-in"), customer_name, notes, pricing_tier, is_quote, employee_id, now(), now()),', '(ticket, table_id, data.get("order_type", "walk-in"), customer_name, notes, pricing_tier, is_quote, employee_id, now(), now(), btype),', 1)

# Scope order/item mutations.
post_block = post_block.replace('item = conn.execute("SELECT * FROM menu_items WHERE id = ? AND active = 1", (int(data["menu_item_id"]),)).fetchone()', 'item = conn.execute("SELECT mi.* FROM menu_items mi JOIN categories c ON c.id = mi.category_id WHERE mi.id = ? AND mi.active = 1 AND c.business_type = ?", (int(data["menu_item_id"]), btype)).fetchone()', 1)
post_block = post_block.replace('order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()', 'order = conn.execute("SELECT * FROM orders WHERE id = ? AND business_type = ?", (order_id, btype)).fetchone()', 1)
post_block = post_block.replace('order = conn.execute("SELECT status, total_cents, customer_name FROM orders WHERE id = ?", (order_id,)).fetchone()', 'order = conn.execute("SELECT status, total_cents, customer_name FROM orders WHERE id = ? AND business_type = ?", (order_id, btype)).fetchone()', 1)

# Customer phone capture isolated to shop category.
post_block = post_block.replace('find_customer_by_phone(conn, payment_ref)', 'find_customer_by_phone(conn, payment_ref, btype)')
post_block = post_block.replace('find_customer_by_phone(conn, customer_phone)', 'find_customer_by_phone(conn, customer_phone, btype)')
post_block = post_block.replace(
    '"INSERT INTO customers(name, phone, notes) VALUES (?, ?, ?)",\n                            (customer_name.strip() or "Customer", normalize_customer_phone(payment_ref), "Auto-saved from M-Pesa purchase"),',
    '"INSERT INTO customers(name, phone, notes, business_type) VALUES (?, ?, ?, ?)",\n                            (customer_name.strip() or "Customer", normalize_customer_phone(payment_ref), "Auto-saved from M-Pesa purchase", btype),',
    1,
)
post_block = post_block.replace(
    '"INSERT INTO customers(name, phone, notes) VALUES (?, ?, ?)",\n                            (customer_name.strip() or "Customer", customer_phone, "Saved from POS checkout"),',
    '"INSERT INTO customers(name, phone, notes, business_type) VALUES (?, ?, ?, ?)",\n                            (customer_name.strip() or "Customer", customer_phone, "Saved from POS checkout", btype),',
    1,
)

# Supplier admin CRUD scoped.
post_block = post_block.replace('"UPDATE suppliers SET name=?, phone=?, email=?, address=?, active=? WHERE id=?",\n                        (name, phone, email, address, active, int(data["id"])),', '"UPDATE suppliers SET name=?, phone=?, email=?, address=?, active=? WHERE id=? AND business_type=?",\n                        (name, phone, email, address, active, int(data["id"]), btype),', 1)
post_block = post_block.replace('"INSERT INTO suppliers(name, phone, email, address, active) VALUES (?, ?, ?, ?, ?)",\n                        (name, phone, email, address, active),', '"INSERT INTO suppliers(name, phone, email, address, active, business_type) VALUES (?, ?, ?, ?, ?, ?)",\n                        (name, phone, email, address, active, btype),', 1)
post_block = post_block.replace('self.send_json(rows(conn.execute("SELECT * FROM suppliers ORDER BY name")))', 'self.send_json(rows(conn.execute("SELECT * FROM suppliers WHERE business_type = ? ORDER BY name", (btype,))))', 1)

# Customer admin CRUD scoped.
post_block = post_block.replace('"UPDATE customers SET name=?, phone=?, email=?, notes=? WHERE id=?",\n                        (name, phone, email, notes, int(data["id"])),', '"UPDATE customers SET name=?, phone=?, email=?, notes=? WHERE id=? AND business_type=?",\n                        (name, phone, email, notes, int(data["id"]), btype),', 1)
post_block = post_block.replace('"INSERT INTO customers(name, phone, email, notes) VALUES (?, ?, ?, ?)",\n                        (name, phone, email, notes),', '"INSERT INTO customers(name, phone, email, notes, business_type) VALUES (?, ?, ?, ?, ?)",\n                        (name, phone, email, notes, btype),', 1)
post_block = post_block.replace('self.send_json(rows(conn.execute("SELECT * FROM customers ORDER BY name")))', 'self.send_json(rows(conn.execute("SELECT * FROM customers WHERE business_type = ? ORDER BY name", (btype,))))', 1)

# Purchases / movements get workspace ownership.
post_block = post_block.replace('"INSERT INTO stock_purchases (supplier_id, product_id, qty_received, cost_per_unit_cents, total_cost_cents, date_received, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",\n                    (supplier_id, product_id, qty, cost, total, now(), user["id"])', '"INSERT INTO stock_purchases (supplier_id, product_id, qty_received, cost_per_unit_cents, total_cost_cents, date_received, created_by, business_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",\n                    (supplier_id, product_id, qty, cost, total, now(), user["id"], btype)', 1)
post_block = post_block.replace('"INSERT INTO stock_movements (product_id, qty_change, reason, note, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",\n                    (product_id, qty, \'purchase\', f\'Supplier {supplier_id}\', user["id"], now())', '"INSERT INTO stock_movements (product_id, qty_change, reason, note, created_by, created_at, business_type) VALUES (?, ?, ?, ?, ?, ?, ?)",\n                    (product_id, qty, \'purchase\', f\'Supplier {supplier_id}\', user["id"], now(), btype)', 1)
post_block = post_block.replace('"INSERT INTO stock_movements(product_id, qty_change, reason, note, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",\n                                (item["menu_item_id"], -item["qty"], "sale", f"Order #{order_id}", user["id"], now()),', '"INSERT INTO stock_movements(product_id, qty_change, reason, note, created_by, created_at, business_type) VALUES (?, ?, ?, ?, ?, ?, ?)",\n                                (item["menu_item_id"], -item["qty"], "sale", f"Order #{order_id}", user["id"], now(), btype),', 1)
post_block = post_block.replace('"INSERT INTO stock_movements(product_id, qty_change, reason, note, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",\n                    (product_id, qty_change, reason, note, user["id"], now()),', '"INSERT INTO stock_movements(product_id, qty_change, reason, note, created_by, created_at, business_type) VALUES (?, ?, ?, ?, ?, ?, ?)",\n                    (product_id, qty_change, reason, note, user["id"], now(), btype),', 1)

# Menu response after changes follows current workspace.
post_block = post_block.replace('settings = get_settings(conn)\n                self.send_json(self.menu_payload(conn, settings.get("business_type")))', 'self.send_json(self.menu_payload(conn, btype))')
py = py[:post_start] + post_block + py[menu_start:]

# ── Tables and admin analytics ─────────────────────────────────────────────────
py = py.replace('    def tables_payload(self, conn):', '    def tables_payload(self, conn, business_type=None):', 1)
py = py.replace("LEFT JOIN orders o ON o.table_id = t.id AND o.status IN ('open', 'sent')", "LEFT JOIN orders o ON o.table_id = t.id AND o.status IN ('open', 'sent') AND (? IS NULL OR o.business_type = ?)", 1)
py = py.replace('            WHERE t.active = 1 ORDER BY t.id\n            """\n        ))', '            WHERE t.active = 1 ORDER BY t.id\n            """, (business_type, business_type)\n        ))', 1)

# Replace admin_summary wholesale: this is where the mixed-shop dashboard came from.
summary_start = py.index('    def admin_summary(self, conn):')
summary_end = py.index('\n    do_DELETE = do_POST', summary_start)
new_summary = '''    def admin_summary(self, conn, business_type):
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
            FROM orders WHERE business_type = ?
            """,
            (day_start, day_start, week_start, business_type),
        ).fetchone())
        by_employee = rows(conn.execute(
            """
            SELECT u.full_name AS employee, COUNT(o.id) AS orders, COALESCE(SUM(o.total_cents), 0) AS sales
            FROM orders o JOIN users u ON u.id = o.created_by
            WHERE o.business_type = ? AND o.status = 'paid' AND o.updated_at >= ?
            GROUP BY u.id, u.full_name ORDER BY sales DESC LIMIT 8
            """, (business_type, week_start),
        ))
        by_method = rows(conn.execute(
            """
            SELECT COALESCE(payment_method, 'unknown') AS method, COUNT(*) AS count, COALESCE(SUM(total_cents), 0) AS sales
            FROM orders
            WHERE business_type = ? AND status = 'paid' AND updated_at >= ?
            GROUP BY payment_method ORDER BY sales DESC
            """, (business_type, week_start),
        ))
        top_items = rows(conn.execute(
            """
            SELECT oi.name, SUM(oi.qty) AS qty, SUM(oi.line_total_cents) AS sales
            FROM order_items oi JOIN orders o ON o.id = oi.order_id
            WHERE o.business_type = ? AND o.status = 'paid' AND o.updated_at >= ?
            GROUP BY oi.name ORDER BY sales DESC LIMIT 8
            """, (business_type, week_start),
        ))
        counts = dict(conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM users WHERE active = 1 AND role NOT IN ('terminal')) AS active_users,
              (SELECT COUNT(*) FROM menu_items mi JOIN categories c ON c.id = mi.category_id WHERE mi.active = 1 AND c.business_type = ?) AS active_items,
              (SELECT COUNT(*) FROM suppliers WHERE active = 1 AND business_type = ?) AS active_suppliers
            """, (business_type, business_type)
        ).fetchone())
        sales_trend = rows(conn.execute(
            """
            SELECT strftime('%Y-%m-%d', updated_at, 'unixepoch', 'localtime') AS day, COALESCE(SUM(total_cents), 0) AS sales
            FROM orders
            WHERE business_type = ? AND status = 'paid' AND updated_at >= ?
            GROUP BY day ORDER BY day ASC
            """, (business_type, week_start)
        ))
        return {"totals": totals, "counts": counts, "by_employee": by_employee, "by_method": by_method, "top_items": top_items, "sales_trend": sales_trend, "business_type": business_type}
'''
py = py[:summary_start] + new_summary + py[summary_end:]

# ── Admin JS: unmistakable workspace badge + genuinely simple promo copy ───────
adm = adm.replace(
    '<h1>Dashboard</h1>\n        <p>Live business overview for ${state.settings?.business_name || state.profile?.name || \'this business\'}</p>',
    '<h1>Dashboard</h1>\n        <p><strong>${state.profile?.icon || \'🏪\'} ${state.profile?.name || \'Business\'} Workspace</strong> · Only this shop category\'s sales and customers are shown here.</p>',
    1,
)

simple_copy = '''const PROMO_PROFILE_COPY = {
  retail: {
    general: 'Thanks for shopping with us. We have fresh stock and great deals available in store. Visit us again soon.',
    stock: 'New stock is in. Drop by and check out what is available.',
    offer: 'We have a special offer running in store. Visit us and enjoy the deal while it lasts.',
    comeback: 'We would love to see you again. Drop by whenever you are around.'
  },
  pharmacy: {
    general: 'Thanks for choosing us. We are here for your pharmacy and wellness needs. Visit us again whenever you need us.',
    stock: 'Fresh pharmacy and wellness stock is available. Visit us or message us to check availability.',
    offer: 'We have offers on selected wellness and personal-care items. Visit us for the current deals.',
    comeback: 'We would be happy to serve you again whenever you need your pharmacy and wellness essentials.'
  },
  restaurant: {
    general: 'Thanks for dining with us. We would love to serve you again. Visit us soon and enjoy your favourite meals.',
    stock: 'Your favourite meals are waiting. Come by and enjoy a fresh meal with us.',
    offer: 'We have a special food offer available. Come by and enjoy it while it lasts.',
    comeback: 'We would love to have you back. Come by for another meal soon.'
  },
  hardware: {
    general: 'Thanks for shopping with us. We are ready to help with your next project. Visit us or message us for stock and quotations.',
    stock: 'New hardware and building-material stock is in. Visit us or message us to check availability.',
    offer: 'We have a special deal on selected hardware and building supplies. Visit us for the current prices.',
    comeback: 'Planning another project? Visit us or send your list and we will help with stock and quotations.'
  },
  boutique: {
    general: 'Thanks for shopping with us. New styles and beauty picks are always coming in. Visit us again soon.',
    stock: 'New arrivals are in. Come by and check out the latest styles, colours and beauty picks.',
    offer: 'We have a special offer on selected fashion and beauty items. Visit us while the deal lasts.',
    comeback: 'We would love to see you again. Come by and check out the latest arrivals.'
  },
  bar: {
    general: 'Thanks for visiting us. Come through again soon for good vibes, drinks and a great time.',
    stock: 'Come through and enjoy good vibes, refreshments and a great time with us.',
    offer: 'We have a special offer at the venue. Come through and enjoy it while it lasts.',
    comeback: 'Come through again soon. We would love to have you back.'
  }
};'''
adm, count = re.subn(r'const PROMO_PROFILE_COPY = \{.*?\n\};', simple_copy, adm, count=1, flags=re.S)
if count != 1:
    raise SystemExit('Could not replace promo copy')
adm, count = re.subn(
    r'function makePromoTemplate\(type, campaign, businessName\) \{.*?\n\}',
    'function makePromoTemplate(type, campaign, businessName) {\n  return promoTemplateBody(type, campaign);\n}',
    adm,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit('Could not simplify promo template')

p.write_text(py)
a.write_text(adm)
