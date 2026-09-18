from pathlib import Path
import re

app_path = Path('app.py')
js_path = Path('static/app.js')
py = app_path.read_text()
js = js_path.read_text()

# 1) Calendar-aware report boundaries in Kenya time.
now_fn = '''def now():
    return int(time.time())
'''
report_helper = '''def now():
    return int(time.time())


def report_period_bounds(period, reference_ts=None, tz_name="Africa/Nairobi"):
    """Return [start, end) epoch bounds for POS reporting in the shop timezone."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    ref_ts = int(reference_ts if reference_ts is not None else now())
    current = datetime.fromtimestamp(ref_ts, tz)
    today_start = current.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "yesterday":
        start_dt = today_start - timedelta(days=1)
        end_dt = today_start
        label = start_dt.strftime("%d %b %Y")
    elif period == "week":
        start_dt = today_start - timedelta(days=6)
        end_dt = current
        label = f"{start_dt.strftime('%d %b')} – {current.strftime('%d %b %Y')}"
    elif period == "month":
        start_dt = today_start - timedelta(days=29)
        end_dt = current
        label = f"{start_dt.strftime('%d %b')} – {current.strftime('%d %b %Y')}"
    else:
        period = "today"
        start_dt = today_start
        end_dt = current
        label = current.strftime("%d %b %Y")

    start_ts = int(start_dt.timestamp())
    # Current-period reports include transactions stamped in the current second.
    end_ts = int(end_dt.timestamp()) + (1 if period != "yesterday" else 0)
    return start_ts, end_ts, label
'''
if 'def report_period_bounds(' not in py:
    if now_fn not in py:
        raise SystemExit('now() marker not found')
    py = py.replace(now_fn, report_helper, 1)

# 2) Persist paid_at and per-line cost snapshots so historical reports don't drift.
orders_migration_old = '''        for col_name, sql in [
            ("table_id", "ALTER TABLE orders ADD COLUMN table_id INTEGER REFERENCES dining_tables(id)"),
            ("pricing_tier", "ALTER TABLE orders ADD COLUMN pricing_tier TEXT NOT NULL DEFAULT 'retail'"),
            ("is_quote", "ALTER TABLE orders ADD COLUMN is_quote INTEGER NOT NULL DEFAULT 0"),
            ("notes", "ALTER TABLE orders ADD COLUMN notes TEXT NOT NULL DEFAULT ''"),
        ]:
'''
orders_migration_new = '''        for col_name, sql in [
            ("table_id", "ALTER TABLE orders ADD COLUMN table_id INTEGER REFERENCES dining_tables(id)"),
            ("pricing_tier", "ALTER TABLE orders ADD COLUMN pricing_tier TEXT NOT NULL DEFAULT 'retail'"),
            ("is_quote", "ALTER TABLE orders ADD COLUMN is_quote INTEGER NOT NULL DEFAULT 0"),
            ("notes", "ALTER TABLE orders ADD COLUMN notes TEXT NOT NULL DEFAULT ''"),
            ("paid_at", "ALTER TABLE orders ADD COLUMN paid_at INTEGER"),
        ]:
'''
if '("paid_at", "ALTER TABLE orders ADD COLUMN paid_at INTEGER")' not in py:
    if orders_migration_old not in py:
        raise SystemExit('orders migration block not found')
    py = py.replace(orders_migration_old, orders_migration_new, 1)

items_migration_old = '''        for col_name, sql in [
            ("variant_info", "ALTER TABLE order_items ADD COLUMN variant_info TEXT NOT NULL DEFAULT ''"),
            ("batch_no", "ALTER TABLE order_items ADD COLUMN batch_no TEXT NOT NULL DEFAULT ''"),
        ]:
            if col_name not in cur_oi_cols:
                conn.execute(sql)

        # Business workspace isolation.'''
items_migration_new = '''        for col_name, sql in [
            ("variant_info", "ALTER TABLE order_items ADD COLUMN variant_info TEXT NOT NULL DEFAULT ''"),
            ("batch_no", "ALTER TABLE order_items ADD COLUMN batch_no TEXT NOT NULL DEFAULT ''"),
            ("cost_cents", "ALTER TABLE order_items ADD COLUMN cost_cents INTEGER"),
        ]:
            if col_name not in cur_oi_cols:
                conn.execute(sql)

        # Backfill report snapshots for existing data. New sales keep these values forever.
        conn.execute("UPDATE orders SET paid_at = updated_at WHERE status = 'paid' AND (paid_at IS NULL OR paid_at = 0)")
        conn.execute("""
            UPDATE order_items
               SET cost_cents = COALESCE((SELECT mi.cost_cents FROM menu_items mi WHERE mi.id = order_items.menu_item_id), 0)
             WHERE cost_cents IS NULL
        """)

        # Business workspace isolation.'''
if '("cost_cents", "ALTER TABLE order_items ADD COLUMN cost_cents INTEGER")' not in py:
    if items_migration_old not in py:
        raise SystemExit('order_items migration block not found')
    py = py.replace(items_migration_old, items_migration_new, 1)

# 3) Snapshot product cost when an item first enters a sale.
insert_old = '''                        INSERT INTO order_items(order_id, menu_item_id, name, qty, unit_price_cents, line_total_cents, note, variant_info, batch_no)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (order_id, item["id"], item["name"], qty, unit_price, int(round(qty * unit_price)), note, variant_info, batch_no),
'''
insert_new = '''                        INSERT INTO order_items(order_id, menu_item_id, name, qty, unit_price_cents, line_total_cents, note, variant_info, batch_no, cost_cents)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (order_id, item["id"], item["name"], qty, unit_price, int(round(qty * unit_price)), note, variant_info, batch_no, item["cost_cents"]),
'''
if 'batch_no, cost_cents)' not in py:
    if insert_old not in py:
        raise SystemExit('order item INSERT not found')
    py = py.replace(insert_old, insert_new, 1)

# 4) Freeze the actual payment timestamp once a sale is paid.
pay_old = '''                conn.execute(
                    "UPDATE orders SET status = 'paid', paid_cents = ?, payment_method = ?, payment_ref = ?, customer_name = ?, updated_at = ? WHERE id = ?",
                    (order["total_cents"], payment_method, payment_ref, customer_name, now(), order_id),
                )
'''
pay_new = '''                paid_ts = now()
                conn.execute(
                    "UPDATE orders SET status = 'paid', paid_cents = ?, payment_method = ?, payment_ref = ?, customer_name = ?, paid_at = COALESCE(paid_at, ?), updated_at = ? WHERE id = ?",
                    (order["total_cents"], payment_method, payment_ref, customer_name, paid_ts, paid_ts, order_id),
                )
'''
if 'paid_at = COALESCE(paid_at, ?)' not in py:
    if pay_old not in py:
        raise SystemExit('payment update block not found')
    py = py.replace(pay_old, pay_new, 1)

# 5) Replace report endpoint with true calendar ranges and snapshot costs.
start = py.find('            elif path == "/api/reports":')
end = py.find('            elif path == "/api/admin/summary":', start)
if start == -1 or end == -1:
    raise SystemExit('report endpoint block not found')
new_reports = '''            elif path == "/api/reports":
                period = query.get("period", ["today"])[0]
                if period not in ("today", "yesterday", "week", "month"):
                    period = "today"
                start_ts, end_ts, range_label = report_period_bounds(period)

                totals = dict(conn.execute(
                    """
                    SELECT
                        COUNT(DISTINCT o.id) AS orders,
                        COALESCE(SUM(oi.line_total_cents), 0) AS sales,
                        COALESCE(SUM(oi.qty * COALESCE(oi.cost_cents, mi.cost_cents, 0)), 0) AS costs,
                        COALESCE(SUM(oi.qty), 0) AS items_sold
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE o.business_type = ?
                      AND o.status = 'paid'
                      AND COALESCE(o.paid_at, o.updated_at) >= ?
                      AND COALESCE(o.paid_at, o.updated_at) < ?
                    """,
                    (btype, start_ts, end_ts),
                ).fetchone())

                payments = rows(conn.execute(
                    """
                    SELECT COALESCE(payment_method, 'cash') AS method,
                           COUNT(*) AS transactions,
                           COALESCE(SUM(total_cents), 0) AS amount
                    FROM orders
                    WHERE business_type = ?
                      AND status = 'paid'
                      AND COALESCE(paid_at, updated_at) >= ?
                      AND COALESCE(paid_at, updated_at) < ?
                    GROUP BY COALESCE(payment_method, 'cash')
                    ORDER BY amount DESC
                    """,
                    (btype, start_ts, end_ts),
                ))

                top_items = rows(conn.execute(
                    """
                    SELECT
                        oi.name,
                        COALESCE(SUM(oi.qty), 0) AS qty,
                        COALESCE(SUM(oi.line_total_cents), 0) AS sales,
                        MAX(mi.stock_qty) AS current_stock
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE o.business_type = ?
                      AND o.status = 'paid'
                      AND COALESCE(o.paid_at, o.updated_at) >= ?
                      AND COALESCE(o.paid_at, o.updated_at) < ?
                    GROUP BY oi.menu_item_id, oi.name
                    ORDER BY sales DESC, qty DESC
                    LIMIT 15
                    """,
                    (btype, start_ts, end_ts),
                ))

                stock_stats = dict(conn.execute(
                    """
                    SELECT
                        COALESCE(SUM(mi.stock_qty * mi.cost_cents), 0) AS inventory_value,
                        COALESCE(SUM(mi.stock_qty * (mi.price_cents - mi.cost_cents)), 0) AS potential_profit
                    FROM menu_items mi
                    JOIN categories c ON c.id = mi.category_id
                    WHERE mi.active = 1 AND mi.stock_qty > 0 AND c.business_type = ?
                    """,
                    (btype,),
                ).fetchone())

                self.send_json({
                    "totals": totals,
                    "payments": payments,
                    "top_items": top_items,
                    "period": period,
                    "range": {"start": start_ts, "end": end_ts, "label": range_label, "timezone": "Africa/Nairobi"},
                    "stock": stock_stats,
                })
'''
py = py[:start] + new_reports + py[end:]

# 6) Make admin dashboard use the same real calendar logic and paid_at timestamp.
admin_start = py.find('    def admin_summary(self, conn, business_type):')
admin_end = py.find('\n    do_DELETE = do_POST', admin_start)
if admin_start == -1 or admin_end == -1:
    raise SystemExit('admin_summary block not found')
admin_block = py[admin_start:admin_end]
admin_block = admin_block.replace('        day_start = now() - 86400\n        week_start = now() - 604800\n', '        day_start, day_end, _ = report_period_bounds("today")\n        week_start, week_end, _ = report_period_bounds("week")\n')
admin_block = admin_block.replace("status = 'paid' AND updated_at >= ?", "status = 'paid' AND COALESCE(paid_at, updated_at) >= ?")
admin_block = admin_block.replace("o.status = 'paid' AND o.updated_at >= ?", "o.status = 'paid' AND COALESCE(o.paid_at, o.updated_at) >= ?")
admin_block = admin_block.replace("WHERE business_type = ? AND status = 'paid' AND updated_at >= ?", "WHERE business_type = ? AND status = 'paid' AND COALESCE(paid_at, updated_at) >= ?")
admin_block = admin_block.replace("strftime('%Y-%m-%d', updated_at, 'unixepoch', 'localtime')", "strftime('%Y-%m-%d', COALESCE(paid_at, updated_at) + 10800, 'unixepoch')")
py = py[:admin_start] + admin_block + py[admin_end:]

# 7) Product click: normal products add immediately. No quantity/note popup.
click_old = '''    if (item.decimal_qty_enabled || hasCap('decimal_qty') || hasCap('order_notes')) {
      showQtyPopup(item);
      return;
    }

    const existing = state.order?.items?.find(i => i.menu_item_id === item.id);
    const existingQty = existing ? existing.qty : 0;
    if (item.stock_qty !== undefined && (1 + existingQty) > item.stock_qty) {
      toast(`Cannot add item. Only ${item.stock_qty} left in stock (you have ${existingQty} in cart).`, 'error');
      return;
    }
    await addItemWithQty(item.id, 1);
'''
click_new = '''    const existing = state.order?.items?.find(i => i.menu_item_id === item.id && !(i.variant_info || ''));
    const existingQty = existing ? Number(existing.qty || 0) : 0;
    if (item.stock_qty !== undefined && (1 + existingQty) > Number(item.stock_qty)) {
      toast(`Cannot add item. Only ${item.stock_qty} left in stock (you have ${existingQty} in cart).`, 'error');
      return;
    }
    await addItemWithQty(item.id, 1, '', '', item.batch_no || '');
'''
if click_old not in js:
    raise SystemExit('normal product click block not found')
js = js.replace(click_old, click_new, 1)

# 8) Variant selection still needs a selector, but after choosing it adds immediately.
variant_old = '''  overlay.querySelectorAll('.variant-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.dataset.idx);
      const selected = variants[idx];
      const vName = typeof selected === 'object' ? selected.name : selected;
      const vPrice = typeof selected === 'object' && selected.price_cents ? selected.price_cents : null;
      close();
      showQtyPopup(item, vName, vPrice);
    });
  });

  overlay.querySelector('#varCustomConfirm').addEventListener('click', () => {
    const val = overlay.querySelector('#customVariantInput').value.trim();
    if (!val) {
      toast('Please enter or select a variant', 'error');
      return;
    }
    close();
    showQtyPopup(item, val);
  });
'''
variant_new = '''  overlay.querySelectorAll('.variant-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const idx = Number(btn.dataset.idx);
      const selected = variants[idx];
      const vName = typeof selected === 'object' ? selected.name : selected;
      const existing = state.order?.items?.find(i => i.menu_item_id === item.id && (i.variant_info || '') === (vName || ''));
      const existingQty = existing ? Number(existing.qty || 0) : 0;
      const variantStock = typeof selected === 'object' && selected.stock_qty !== undefined ? Number(selected.stock_qty) : Number(item.stock_qty);
      if (Number.isFinite(variantStock) && (1 + existingQty) > variantStock) {
        toast(`Cannot add ${vName}. Only ${variantStock} left in stock.`, 'error');
        return;
      }
      close();
      await addItemWithQty(item.id, 1, vName || '', '', item.batch_no || '');
    });
  });

  overlay.querySelector('#varCustomConfirm').addEventListener('click', async () => {
    const val = overlay.querySelector('#customVariantInput').value.trim();
    if (!val) {
      toast('Please enter or select a variant', 'error');
      return;
    }
    close();
    await addItemWithQty(item.id, 1, val, '', item.batch_no || '');
  });
'''
if variant_old not in js:
    raise SystemExit('variant selection block not found')
js = js.replace(variant_old, variant_new, 1)

# 9) Improve report UI labels and printed report branding/range.
js = js.replace(
    '<h2>Business Analytics</h2>',
    '<div><h2 style="margin:0">Business Analytics</h2><div style="font-size:12px;color:var(--muted);margin-top:4px;">${report.range?.label || \'Selected period\'} · ${state.profile?.name || \'POS\'}</div></div>',
    1,
)
js = js.replace('>Cash in Drawer</div>', '>Cash Sales</div>', 1)

inventory_card_end = '''      <div style="background: white; padding: 20px; border-radius: 12px; border: 1px solid var(--line); box-shadow: 0 4px 12px rgba(0,0,0,0.02);">
        <div style="font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase;">Cash Sales</div>
        <div style="font-size: 28px; font-weight: 800; color: #16a34a; margin-top: 8px;">${money(cashTotal)}</div>
      </div>
'''
mpesa_card = inventory_card_end + '''      <div style="background: white; padding: 20px; border-radius: 12px; border: 1px solid var(--line); box-shadow: 0 4px 12px rgba(0,0,0,0.02);">
        <div style="font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase;">M-Pesa Sales</div>
        <div style="font-size: 28px; font-weight: 800; color: #16a34a; margin-top: 8px;">${money(mpesaTotal)}</div>
      </div>
'''
if inventory_card_end in js and 'M-Pesa Sales</div>' not in js:
    js = js.replace(inventory_card_end, mpesa_card, 1)

js = js.replace('<h2>NIGHTCLUB POS</h2>', '<h2>${state.settings?.business_name || state.profile?.name || \'POS\'}</h2>', 1)
js = js.replace('<p style="margin:0">Z-REPORT (${period.toUpperCase()})</p>', '<p style="margin:0">Z-REPORT · ${report.range?.label || period.toUpperCase()}</p>', 1)

app_path.write_text(py)
js_path.write_text(js)
print('Patched report accounting/date logic and instant product add-to-cart.')
