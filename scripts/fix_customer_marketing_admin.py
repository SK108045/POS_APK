from pathlib import Path
import re

app_py = Path('app.py')
app_js = Path('static/app.js')
admin_js = Path('static/admin.js')

py = app_py.read_text()
js = app_js.read_text()
adm = admin_js.read_text()

# ---------------- POS: optional customer phone at checkout ----------------
phone_block = '''      <div style="margin-bottom: 16px;">
        <label style="display:block; margin-bottom: 8px; font-weight: 600;">Customer Phone <span style="font-weight:400;color:var(--muted)">(optional)</span></label>
        <input type="tel" id="checkoutCustomerPhone" class="field" placeholder="e.g. 0712345678" style="width: 100%; padding: 10px;" autocomplete="tel">
        <small style="display:block;margin-top:6px;color:var(--muted);">If entered, the number is saved to Customers after payment. M-Pesa uses its payment phone automatically.</small>
      </div>

'''
payment_marker = '''      <div style="margin-bottom: 16px;">
        <label style="display:block; margin-bottom: 8px; font-weight: 600;">Payment Method</label>'''
if 'id="checkoutCustomerPhone"' not in js:
    if payment_marker not in js:
        raise SystemExit('checkout payment marker not found')
    js = js.replace(payment_marker, phone_block + payment_marker, 1)

const_marker = "  const refInput = overlay.querySelector('#mpesaRef');\n"
if "checkoutCustomerPhone" in js and "const customerPhoneInput = overlay.querySelector('#checkoutCustomerPhone');" not in js:
    if const_marker not in js:
        raise SystemExit('checkout ref input marker not found')
    js = js.replace(const_marker, const_marker + "  const customerPhoneInput = overlay.querySelector('#checkoutCustomerPhone');\n", 1)

ref_marker = "    const ref = refInput.value.trim();\n"
if "const customerPhone =" not in js:
    if ref_marker not in js:
        raise SystemExit('checkout ref value marker not found')
    js = js.replace(ref_marker, ref_marker + "    const customerPhone = (customerPhoneInput?.value || '').trim() || (method === 'mpesa' ? ref : '');\n", 1)

old_pay_body = "body: { order_id: order.id, payment_method: method, payment_ref: ref }"
new_pay_body = "body: { order_id: order.id, payment_method: method, payment_ref: ref, customer_phone: customerPhone }"
if old_pay_body in js:
    js = js.replace(old_pay_body, new_pay_body, 1)
elif new_pay_body not in js:
    raise SystemExit('order pay payload marker not found')

js = js.replace('>MPESA No</label>', '>M-Pesa / STK Phone</label>', 1)
js = js.replace("msgEl.textContent = 'Please enter MPESA No.';", "msgEl.textContent = 'Please enter the M-Pesa / STK phone number.';", 1)

# ---------------- Backend: normalize and save customer phone ----------------
rows_marker = '''def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]
'''
helpers = '''def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]


def normalize_customer_phone(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if not digits:
        return ''
    if len(digits) == 10 and digits.startswith('0'):
        digits = '254' + digits[1:]
    elif len(digits) == 9 and digits[0] in ('7', '1'):
        digits = '254' + digits
    return digits


def find_customer_by_phone(conn, value):
    target = normalize_customer_phone(value)
    if not target:
        return None
    for row in conn.execute("SELECT id, name, phone FROM customers").fetchall():
        if normalize_customer_phone(row['phone']) == target:
            return row
    return None
'''
if 'def normalize_customer_phone(' not in py:
    if rows_marker not in py:
        raise SystemExit('rows helper marker not found')
    py = py.replace(rows_marker, helpers, 1)

pay_vars = '''                payment_method = data.get("payment_method", "cash")
                payment_ref = data.get("payment_ref", "").strip()
                customer_name = order["customer_name"]
'''
new_pay_vars = '''                payment_method = data.get("payment_method", "cash")
                payment_ref = data.get("payment_ref", "").strip()
                customer_phone = normalize_customer_phone(data.get("customer_phone", ""))
                if payment_method == "mpesa":
                    payment_ref = normalize_customer_phone(payment_ref) or payment_ref
                    customer_phone = customer_phone or normalize_customer_phone(payment_ref)
                customer_name = order["customer_name"]
'''
if 'customer_phone = normalize_customer_phone(data.get("customer_phone"' not in py:
    if pay_vars not in py:
        raise SystemExit('payment variable block not found')
    py = py.replace(pay_vars, new_pay_vars, 1)

# Replace M-Pesa-specific customer auto-save with normalized lookup, without forcing fake Customer N names onto receipts.
pattern = re.compile(r'''\n\s{20}# Auto-save customer\n\s{20}customer = conn\.execute\("SELECT id, name FROM customers WHERE phone = \?", \(payment_ref,\)\)\.fetchone\(\)\n.*?(?=\n\s{16}conn\.execute\(\n\s{20}"UPDATE orders SET status)''', re.S)
replacement = '''
                    # Save the M-Pesa/STK phone into Customers after a successful payment.
                    customer = find_customer_by_phone(conn, payment_ref)
                    if not customer:
                        conn.execute(
                            "INSERT INTO customers(name, phone, notes) VALUES (?, ?, ?)",
                            (customer_name.strip() or "Customer", normalize_customer_phone(payment_ref), "Auto-saved from M-Pesa purchase"),
                        )
'''
py2, n = pattern.subn(replacement, py, count=1)
if n == 1:
    py = py2
elif 'Auto-saved from M-Pesa purchase' in py and 'find_customer_by_phone(conn, payment_ref)' not in py:
    raise SystemExit('could not replace M-Pesa customer auto-save block')

# Cash/card/etc: optional entered phone should also become a customer contact.
update_marker = '''                conn.execute(
                    "UPDATE orders SET status = 'paid', paid_cents = ?, payment_method = ?, payment_ref = ?, customer_name = ?, updated_at = ? WHERE id = ?",
'''
optional_save = '''                if payment_method != "mpesa" and customer_phone:
                    customer = find_customer_by_phone(conn, customer_phone)
                    if not customer:
                        conn.execute(
                            "INSERT INTO customers(name, phone, notes) VALUES (?, ?, ?)",
                            (customer_name.strip() or "Customer", customer_phone, "Saved from POS checkout"),
                        )

'''
if 'Saved from POS checkout' not in py:
    if update_marker not in py:
        raise SystemExit('order update marker not found')
    py = py.replace(update_marker, optional_save + update_marker, 1)

# ---------------- Marketing copy: natural, no customer-name personalization ----------------
new_copy = '''const PROMO_PROFILE_COPY = {
  retail: {
    general: 'Thanks for shopping with us! We have fresh stock and great value in store, and we would love to see you again soon.',
    stock: 'New stock has arrived! Drop by and check out what is new in store.',
    offer: 'We have a special offer running in store. Visit us and enjoy the deal while it lasts.',
    comeback: 'It has been a while since your last visit. We would love to welcome you back soon.'
  },
  pharmacy: {
    general: 'Thanks for choosing us. We are here whenever you need pharmacy, wellness and personal-care essentials. We look forward to serving you again.',
    stock: 'Fresh pharmacy, wellness and personal-care stock is now available. Feel free to check with us before your next visit.',
    offer: 'We have special offers on selected wellness and personal-care items. Visit us for the current deals.',
    comeback: 'We would be happy to serve you again. Visit us whenever you need your pharmacy, wellness or personal-care essentials.'
  },
  restaurant: {
    general: 'Thanks for dining with us! We would love to have you back for another meal. Come by and enjoy your favourites again soon.',
    stock: 'Fresh dishes and your favourites are waiting for you. Come by and enjoy a great meal with us.',
    offer: 'We have a special food offer available. Come by and enjoy it while it lasts.',
    comeback: 'We miss having you around! Come back for another meal soon — we would love to serve you again.'
  },
  hardware: {
    general: 'Thanks for shopping with us! For your next project, we are ready with hardware, tools and building supplies. Send us your list anytime and we will help you check availability or prepare a quote.',
    stock: 'New hardware and building-material stock has arrived. Send us your list or visit us to check availability.',
    offer: 'We have a special deal on selected hardware and building supplies. Visit us for the current prices and offers.',
    comeback: 'Planning another project? We are ready to help with your hardware list, stock checks and quotations.'
  },
  boutique: {
    general: 'Thanks for shopping with us! New styles, colours and beauty picks are always coming in. We would love to see you again soon.',
    stock: 'New arrivals are in! Come by and check out the latest styles, colours, sizes and beauty picks.',
    offer: 'We have a special offer on selected fashion, beauty and cosmetics items. Visit us and enjoy the deal while it lasts.',
    comeback: 'It has been a while since your last visit. Come see the latest arrivals — we would love to have you back.'
  },
  bar: {
    general: 'Thanks for spending time with us! We would love to have you back for another good time. See you again soon.',
    stock: 'There is something fresh happening at the venue. Come by for good vibes, refreshments and a great time.',
    offer: 'We have a special offer at the venue. Come through and enjoy it while it lasts.',
    comeback: 'It has been a while since your last visit. Come through again soon — we would love to have you back.'
  }
};'''
adm, n = re.subn(r'const PROMO_PROFILE_COPY = \{.*?\n\};', new_copy, adm, count=1, flags=re.S)
if n != 1:
    raise SystemExit('promo profile copy block not found')

adm, n = re.subn(
    r'''function makePromoTemplate\(type, campaign, businessName\) \{.*?\n\}''',
    '''function makePromoTemplate(type, campaign, businessName) {\n  const body = promoTemplateBody(type, campaign);\n  return `${body}\\n\\n— ${businessName}`;\n}''',
    adm,
    count=1,
    flags=re.S,
)
if n != 1:
    raise SystemExit('makePromoTemplate function not found')

adm, n = re.subn(
    r'''function personalizePromoMessage\(template, customer\) \{.*?\n\}''',
    '''function personalizePromoMessage(template, customer) {\n  const businessName = state.promoSettings?.business_name || 'Our business';\n  return String(template || '').replaceAll('{business_name}', businessName);\n}''',
    adm,
    count=1,
    flags=re.S,
)
if n != 1:
    raise SystemExit('personalizePromoMessage function not found')

adm = adm.replace(
    'Use <code>{name}</code> for the customer\'s name and <code>{business_name}</code> for the business name.',
    'Edit the message however you like before opening WhatsApp.'
)

# Remove old hard-coded EITY FIT PR button from Customers; the Promotions page is now the single marketing flow.
adm = re.sub(r'''\s*<a class="btn btn-primary btn-sm" href="https://wa\.me/\$\{c\.phone\.replace\(/\\\+/g,''\)\.replace\(/\^0/, '254'\)\}\?text=Thank%20you%20for%20shopping%20at%20EITY%20FIT%21%20We%20value%20your%20business\." target="_blank" style="text-decoration:none; display:inline-flex;">Send PR Message</a>''', '', adm, count=1)

# ---------------- Admin portal: reflect current shop/profile ----------------
py = py.replace('<div class="logo-icon">B</div>\n          <span class="name">EITY FIT</span>', '<div class="logo-icon" id="adminBusinessIcon">🛒</div>\n          <span class="name" id="adminBusinessName">POS</span>', 1)
py = py.replace('<div class="tag">Admin Portal</div>', '<div class="tag" id="adminPortalTag">Admin Portal</div>', 1)
py = py.replace('<span class="nav-label">Products</span>', '<span class="nav-label" id="adminProductsLabel">Products</span>', 1)

adm = adm.replace(
    '<p>Live business overview for EITY FIT Retail POS</p>',
    '<p>Live business overview for ${state.settings?.business_name || state.profile?.name || \'this business\'}</p>',
    1,
)

boot_marker = '''  state.user = data.user;
  if (state.user.role !== 'manager') { location.href = '/admin'; return; }
'''
boot_replacement = '''  state.user = data.user;
  state.settings = data.settings || {};
  state.profile = data.profile || {};
  if (state.user.role !== 'manager') { location.href = '/admin'; return; }

  const businessName = state.settings.business_name || state.profile.name || 'POS';
  const profileName = state.profile.name || 'Business';
  const businessIcon = state.profile.icon || '🏪';
  const itemLabel = state.profile.item_label || 'Products';
  const businessNameEl = $('#adminBusinessName');
  const businessIconEl = $('#adminBusinessIcon');
  const portalTagEl = $('#adminPortalTag');
  const productsLabelEl = $('#adminProductsLabel');
  if (businessNameEl) businessNameEl.textContent = businessName;
  if (businessIconEl) businessIconEl.textContent = businessIcon;
  if (portalTagEl) portalTagEl.textContent = `${profileName} Admin`;
  if (productsLabelEl) productsLabelEl.textContent = itemLabel;
  document.title = `${businessName} — Admin Portal`;
'''
if 'state.settings = data.settings || {};' not in adm:
    if boot_marker not in adm:
        raise SystemExit('admin boot marker not found')
    adm = adm.replace(boot_marker, boot_replacement, 1)

app_py.write_text(py)
app_js.write_text(js)
admin_js.write_text(adm)
