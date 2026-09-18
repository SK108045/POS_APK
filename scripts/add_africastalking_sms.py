from pathlib import Path

app_path = Path('app.py')
admin_path = Path('static/admin.js')
req_path = Path('requirements.txt')

app = app_path.read_text()
admin = admin_path.read_text()
req = req_path.read_text()

# ---------------------------------------------------------------------------
# Backend config helper
# ---------------------------------------------------------------------------
anchor = 'STORE_TAGLINE = "Bar & Club POS"\n\n\n'
helper = '''STORE_TAGLINE = "Bar & Club POS"\n\n\ndef africastalking_sms_config():\n    """Return SMS configuration without ever exposing the API key to the browser."""\n    import os\n\n    username = os.environ.get("AFRICASTALKING_USERNAME", "sk10").strip() or "sk10"\n    api_key = os.environ.get("AFRICASTALKING_API_KEY", "").strip()\n    if not api_key:\n        key_file = BASE_DIR / "api.txt"\n        if key_file.exists():\n            api_key = key_file.read_text(encoding="utf-8").strip()\n\n    demo_number = os.environ.get("AFRICASTALKING_DEMO_NUMBER", "+254756205063").strip() or "+254756205063"\n    return {\n        "username": username,\n        "api_key": api_key,\n        "demo_number": demo_number,\n        "configured": bool(username and api_key),\n    }\n\n\ndef send_africastalking_sms(message, recipients):\n    cfg = africastalking_sms_config()\n    if not cfg["configured"]:\n        raise RuntimeError("Africa's Talking API key is not configured on the server")\n\n    try:\n        import africastalking\n    except ImportError as exc:\n        raise RuntimeError("Africa's Talking package is not installed. Run pip install -r requirements.txt") from exc\n\n    africastalking.initialize(cfg["username"], cfg["api_key"])\n    return africastalking.SMS.send(message, recipients, timeout=30)\n\n\n'''
if anchor not in app:
    raise SystemExit('STORE_TAGLINE anchor not found')
if 'def africastalking_sms_config()' not in app:
    app = app.replace(anchor, helper, 1)

# ---------------------------------------------------------------------------
# GET config endpoint - no secret returned
# ---------------------------------------------------------------------------
old_get = '''            elif path == "/api/admin/customers":\n                self.send_json(rows(conn.execute("SELECT * FROM customers WHERE business_type = ? ORDER BY name", (btype,))))\n            elif path == "/api/admin/users":\n'''
new_get = '''            elif path == "/api/admin/customers":\n                self.send_json(rows(conn.execute("SELECT * FROM customers WHERE business_type = ? ORDER BY name", (btype,))))\n            elif path == "/api/admin/sms/config":\n                if not self.require_manager(user):\n                    return\n                sms_cfg = africastalking_sms_config()\n                self.send_json({\n                    "provider": "Africa's Talking",\n                    "configured": sms_cfg["configured"],\n                    "username": sms_cfg["username"],\n                    "demo_mode": True,\n                    "demo_number": sms_cfg["demo_number"],\n                })\n            elif path == "/api/admin/users":\n'''
if old_get not in app:
    raise SystemExit('admin customers GET block not found')
if '/api/admin/sms/config' not in app:
    app = app.replace(old_get, new_get, 1)

# ---------------------------------------------------------------------------
# POST live SMS endpoint. Demo mode always forces the single demo recipient.
# ---------------------------------------------------------------------------
old_post = '''            elif path == "/api/admin/customer":\n                name = data.get("name", "").strip()\n                phone = data.get("phone", "").strip()\n                email = data.get("email", "").strip()\n                notes = data.get("notes", "").strip()\n                if not name:\n                    return self.send_json({"error": "missing_customer_name"}, 400)\n                if data.get("id"):\n                    conn.execute(\n                        "UPDATE customers SET name=?, phone=?, email=?, notes=? WHERE id=? AND business_type=?",\n                        (name, phone, email, notes, int(data["id"]), btype),\n                    )\n                else:\n                    conn.execute(\n                        "INSERT INTO customers(name, phone, email, notes, business_type) VALUES (?, ?, ?, ?, ?)",\n                        (name, phone, email, notes, btype),\n                    )\n                self.send_json(rows(conn.execute("SELECT * FROM customers WHERE business_type = ? ORDER BY name", (btype,))))\n            elif path == "/api/stock/adjust":\n'''
new_post = '''            elif path == "/api/admin/customer":\n                name = data.get("name", "").strip()\n                phone = data.get("phone", "").strip()\n                email = data.get("email", "").strip()\n                notes = data.get("notes", "").strip()\n                if not name:\n                    return self.send_json({"error": "missing_customer_name"}, 400)\n                if data.get("id"):\n                    conn.execute(\n                        "UPDATE customers SET name=?, phone=?, email=?, notes=? WHERE id=? AND business_type=?",\n                        (name, phone, email, notes, int(data["id"]), btype),\n                    )\n                else:\n                    conn.execute(\n                        "INSERT INTO customers(name, phone, email, notes, business_type) VALUES (?, ?, ?, ?, ?)",\n                        (name, phone, email, notes, btype),\n                    )\n                self.send_json(rows(conn.execute("SELECT * FROM customers WHERE business_type = ? ORDER BY name", (btype,))))\n            elif path == "/api/admin/sms/send":\n                if not self.require_manager(user):\n                    return\n                message = str(data.get("message", "")).strip()\n                if not message:\n                    return self.send_json({"error": "Write an SMS message first"}, 400)\n                if len(message) > 1000:\n                    return self.send_json({"error": "SMS message is too long (maximum 1000 characters)"}, 400)\n\n                sms_cfg = africastalking_sms_config()\n                demo_number = sms_cfg["demo_number"]\n                try:\n                    result = send_africastalking_sms(message, [demo_number])\n                except Exception as exc:\n                    # Never return credentials or configuration internals to the browser.\n                    error_text = str(exc).replace(sms_cfg.get("api_key", ""), "***")\n                    return self.send_json({"error": error_text[:300] or "SMS send failed"}, 502)\n\n                sms_data = result.get("SMSMessageData", {}) if isinstance(result, dict) else {}\n                recipients = sms_data.get("Recipients", []) if isinstance(sms_data, dict) else []\n                recipient_result = recipients[0] if recipients else {}\n                self.send_json({\n                    "ok": True,\n                    "provider": "Africa's Talking",\n                    "demo_mode": True,\n                    "recipient": demo_number,\n                    "status": recipient_result.get("status") or sms_data.get("Message") or "Sent",\n                    "message_id": recipient_result.get("messageId") or recipient_result.get("message_id"),\n                    "cost": recipient_result.get("cost"),\n                })\n            elif path == "/api/stock/adjust":\n'''
if old_post not in app:
    raise SystemExit('admin customer POST block not found')
if '/api/admin/sms/send' not in app:
    app = app.replace(old_post, new_post, 1)

# ---------------------------------------------------------------------------
# Admin sidebar wording + cache busting for admin assets
# ---------------------------------------------------------------------------
app = app.replace('<span class="nav-label">WhatsApp Promotions</span>', '<span class="nav-label">Customer Marketing</span>')
app = app.replace('/static/admin.css?v=1782846743.6849699', '/static/admin.css?v=__ASSET_VERSION__')
app = app.replace('/static/admin.js?v=1782848139.5770284', '/static/admin.js?v=__ASSET_VERSION__')
old_return = '''    return (html\n            .replace("__SHOP_ICON__", profile.get("icon", "🏪"))\n            .replace("__SHOP_NAME__", profile.get("name", business_type)))\n'''
new_return = '''    return (html\n            .replace("__SHOP_ICON__", profile.get("icon", "🏪"))\n            .replace("__SHOP_NAME__", profile.get("name", business_type))\n            .replace("__ASSET_VERSION__", str(int(time.time()))))\n'''
if old_return in app:
    app = app.replace(old_return, new_return, 1)
elif '__ASSET_VERSION__' in app and '.replace("__ASSET_VERSION__"' not in app:
    raise SystemExit('hidden_admin_page return block not found for asset version')

# ---------------------------------------------------------------------------
# Frontend: load SMS config along with customers and profile
# ---------------------------------------------------------------------------
old_fetch = '''    const [customers, settingsPayload] = await Promise.all([\n      api('/api/admin/customers'),\n      api('/api/settings')\n    ]);\n    state.promoCustomers = (customers || []).filter(c => String(c.phone || '').trim());\n    state.promoSettings = settingsPayload?.settings || {};\n    state.promoProfile = settingsPayload?.profile || {};\n'''
new_fetch = '''    const [customers, settingsPayload, smsConfig] = await Promise.all([\n      api('/api/admin/customers'),\n      api('/api/settings'),\n      api('/api/admin/sms/config')\n    ]);\n    state.promoCustomers = (customers || []).filter(c => String(c.phone || '').trim());\n    state.promoSettings = settingsPayload?.settings || {};\n    state.promoProfile = settingsPayload?.profile || {};\n    state.smsConfig = smsConfig || {};\n'''
if old_fetch not in admin:
    raise SystemExit('promotion Promise.all block not found')
admin = admin.replace(old_fetch, new_fetch, 1)

admin = admin.replace('<h1>WhatsApp Promotions</h1>', '<h1>Customer Marketing</h1>', 1)
admin = admin.replace('Customer promotions tailored for ${promoEscape(profileName)}', 'WhatsApp and SMS promotions tailored for ${promoEscape(profileName)}', 1)
admin = admin.replace('Edit the message however you like before opening WhatsApp.', 'Edit the message however you like. The same campaign text can be used for WhatsApp or SMS.', 1)

old_actions = '''          <div class="promo-actions">\n            <button class="btn btn-ghost" id="promoResetBtn">Reset Template</button>\n            <button class="btn btn-primary" id="promoPrepareBtn">Prepare Selected Messages</button>\n          </div>\n'''
new_actions = '''          <div class="promo-hint" id="promoSmsCharCount" style="margin-top:8px">0 characters · 1 SMS segment</div>\n          <div class="promo-actions">\n            <button class="btn btn-ghost" id="promoResetBtn">Reset Template</button>\n            <button class="btn btn-primary" id="promoPrepareBtn">Prepare WhatsApp Messages</button>\n          </div>\n'''
if old_actions not in admin:
    raise SystemExit('promotion actions block not found')
admin = admin.replace(old_actions, new_actions, 1)

queue_marker = '''    <div class="panel promo-queue-panel" id="promoQueuePanel" style="display:none">\n'''
sms_panel = '''    <div class="panel" style="margin-top:20px">\n      <div class="panel-header">\n        <div>\n          <div class="panel-title">SMS Marketing · Africa's Talking</div>\n          <div class="panel-subtitle">Live SMS sending from the POS server</div>\n        </div>\n        <span class="badge badge-active">DEMO MODE</span>\n      </div>\n      <div class="panel-body">\n        <div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:end">\n          <div>\n            <div class="form-label">Demo recipient</div>\n            <div style="font-size:16px;font-weight:800;margin-top:4px" id="promoSmsRecipient">${promoEscape(state.smsConfig?.demo_number || '+254756205063')}</div>\n            <div class="promo-hint" style="margin-top:8px">For now SMS is locked to this demo Airtel number so a marketing test cannot accidentally message your saved customers. The message comes from the campaign editor above.</div>\n            <div class="promo-hint" style="margin-top:5px">Provider status: <strong>${state.smsConfig?.configured ? 'Configured' : 'API key not configured on server'}</strong></div>\n          </div>\n          <button class="btn btn-primary" id="promoSmsSendBtn" ${state.smsConfig?.configured ? '' : 'disabled'}>Send Demo SMS</button>\n        </div>\n        <div id="promoSmsStatus" style="margin-top:12px"></div>\n      </div>\n    </div>\n\n'''
if queue_marker not in admin:
    raise SystemExit('promo queue marker not found')
admin = admin.replace(queue_marker, sms_panel + queue_marker, 1)

old_listeners = '''  $('#promoCampaignType').addEventListener('change', resetPromoTemplate);\n  $('#promoResetBtn').addEventListener('click', resetPromoTemplate);\n  $('#promoPrepareBtn').addEventListener('click', preparePromoQueue);\n'''
new_listeners = '''  $('#promoCampaignType').addEventListener('change', resetPromoTemplate);\n  $('#promoResetBtn').addEventListener('click', resetPromoTemplate);\n  $('#promoPrepareBtn').addEventListener('click', preparePromoQueue);\n  $('#promoMessageEditor').addEventListener('input', updatePromoSmsCounter);\n  $('#promoSmsSendBtn')?.addEventListener('click', sendPromoSmsDemo);\n  updatePromoSmsCounter();\n'''
if old_listeners not in admin:
    raise SystemExit('promotion listeners block not found')
admin = admin.replace(old_listeners, new_listeners, 1)

old_reset_tail = '''  const editor = $('#promoMessageEditor');\n  if (editor) editor.value = makePromoTemplate(type, campaign, businessName);\n}\n\nfunction renderPromoCustomerRows'''
new_reset_tail = '''  const editor = $('#promoMessageEditor');\n  if (editor) editor.value = makePromoTemplate(type, campaign, businessName);\n  updatePromoSmsCounter();\n}\n\nfunction updatePromoSmsCounter() {\n  const editor = $('#promoMessageEditor');\n  const label = $('#promoSmsCharCount');\n  if (!editor || !label) return;\n  const length = editor.value.length;\n  const segments = Math.max(1, Math.ceil(length / 160));\n  label.textContent = `${length} characters · ${segments} SMS segment${segments === 1 ? '' : 's'}`;\n}\n\nasync function sendPromoSmsDemo() {\n  const editor = $('#promoMessageEditor');\n  const button = $('#promoSmsSendBtn');\n  const status = $('#promoSmsStatus');\n  const message = editor?.value?.trim() || '';\n  if (!message) {\n    toast('Write a promotion message first.', 'error');\n    return;\n  }\n  const number = state.smsConfig?.demo_number || '+254756205063';\n  if (!confirm(`Send this live SMS through Africa's Talking to ${number}?`)) return;\n\n  const oldText = button?.textContent;\n  if (button) { button.disabled = true; button.textContent = 'Sending…'; }\n  if (status) status.innerHTML = '<span style="color:var(--muted)">Sending through Africa\'s Talking…</span>';\n  try {\n    const result = await api('/api/admin/sms/send', { method:'POST', body:{ message } });\n    const detail = [result.status, result.cost].filter(Boolean).join(' · ');\n    if (status) status.innerHTML = `<div style="padding:10px 12px;border-radius:8px;background:#dcfce7;color:#166534;font-weight:700">✓ SMS sent to ${promoEscape(result.recipient || number)}${detail ? ` · ${promoEscape(detail)}` : ''}</div>`;\n    toast('Demo SMS sent successfully');\n  } catch (e) {\n    if (status) status.innerHTML = `<div style="padding:10px 12px;border-radius:8px;background:#fee2e2;color:#991b1b;font-weight:700">${promoEscape(e.message)}</div>`;\n    toast(e.message, 'error');\n  } finally {\n    if (button) { button.disabled = false; button.textContent = oldText || 'Send Demo SMS'; }\n  }\n}\n\nfunction renderPromoCustomerRows'''
if old_reset_tail not in admin:
    raise SystemExit('resetPromoTemplate tail not found')
admin = admin.replace(old_reset_tail, new_reset_tail, 1)

# Keep selection button wording accurate after count updates.
admin = admin.replace("btn.textContent = `Prepare Selected Messages (${state.promoSelected?.size || 0})`;", "btn.textContent = `Prepare WhatsApp Messages (${state.promoSelected?.size || 0})`;", 1)

# Requirements
if 'africastalking' not in req.lower():
    if req and not req.endswith('\n'):
        req += '\n'
    req += 'africastalking\n'

app_path.write_text(app)
admin_path.write_text(admin)
req_path.write_text(req)
