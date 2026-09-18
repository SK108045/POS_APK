from pathlib import Path

app_path = Path('app.py')
admin_path = Path('static/admin.js')

app = app_path.read_text()
admin = admin_path.read_text()

old_config = '''            elif path == "/api/admin/sms/config":
                if not self.require_manager(user):
                    return
                sms_cfg = africastalking_sms_config()
                self.send_json({
                    "provider": "Africa's Talking",
                    "configured": sms_cfg["configured"],
                    "username": sms_cfg["username"],
                    "demo_mode": True,
                    "demo_number": sms_cfg["demo_number"],
                })
'''
new_config = '''            elif path == "/api/admin/sms/config":
                if not self.require_manager(user):
                    return
                sms_cfg = africastalking_sms_config()
                self.send_json({
                    "provider": "Africa's Talking",
                    "configured": sms_cfg["configured"],
                    "username": sms_cfg["username"],
                    "bulk_enabled": True,
                })
'''
if old_config not in app:
    raise SystemExit('SMS config block not found')
app = app.replace(old_config, new_config, 1)

old_endpoint = '''            elif path == "/api/admin/sms/send":
                if not self.require_manager(user):
                    return
                message = str(data.get("message", "")).strip()
                if not message:
                    return self.send_json({"error": "Write an SMS message first"}, 400)
                if len(message) > 1000:
                    return self.send_json({"error": "SMS message is too long (maximum 1000 characters)"}, 400)

                sms_cfg = africastalking_sms_config()
                demo_number = sms_cfg["demo_number"]
                try:
                    result = send_africastalking_sms(message, [demo_number])
                except Exception as exc:
                    # Never return credentials or configuration internals to the browser.
                    error_text = str(exc).replace(sms_cfg.get("api_key", ""), "***")
                    return self.send_json({"error": error_text[:300] or "SMS send failed"}, 502)

                sms_data = result.get("SMSMessageData", {}) if isinstance(result, dict) else {}
                recipients = sms_data.get("Recipients", []) if isinstance(sms_data, dict) else []
                recipient_result = recipients[0] if recipients else {}
                self.send_json({
                    "ok": True,
                    "provider": "Africa's Talking",
                    "demo_mode": True,
                    "recipient": demo_number,
                    "status": recipient_result.get("status") or sms_data.get("Message") or "Sent",
                    "message_id": recipient_result.get("messageId") or recipient_result.get("message_id"),
                    "cost": recipient_result.get("cost"),
                })
'''
new_endpoint = '''            elif path == "/api/admin/sms/send":
                if not self.require_manager(user):
                    return
                message = str(data.get("message", "")).strip()
                if not message:
                    return self.send_json({"error": "Write an SMS message first"}, 400)
                if len(message) > 1000:
                    return self.send_json({"error": "SMS message is too long (maximum 1000 characters)"}, 400)

                raw_ids = data.get("customer_ids") or []
                if not isinstance(raw_ids, list):
                    return self.send_json({"error": "Select customers before sending SMS"}, 400)
                try:
                    customer_ids = sorted({int(value) for value in raw_ids if int(value) > 0})
                except (TypeError, ValueError):
                    return self.send_json({"error": "Invalid customer selection"}, 400)
                if not customer_ids:
                    return self.send_json({"error": "Select at least one customer first"}, 400)
                if len(customer_ids) > 200:
                    return self.send_json({"error": "Send to at most 200 customers at a time"}, 400)

                placeholders = ",".join("?" for _ in customer_ids)
                selected_customers = rows(conn.execute(
                    f"SELECT id, name, phone FROM customers WHERE business_type = ? AND id IN ({placeholders}) ORDER BY name",
                    [btype] + customer_ids,
                ))

                recipients = []
                seen = set()
                skipped = 0
                for customer in selected_customers:
                    digits = "".join(ch for ch in str(customer.get("phone") or "") if ch.isdigit())
                    if len(digits) == 10 and digits.startswith("0"):
                        digits = "254" + digits[1:]
                    elif len(digits) == 9 and digits[:1] in ("7", "1"):
                        digits = "254" + digits
                    phone = "+" + digits if 10 <= len(digits) <= 15 else ""
                    if not phone or phone in seen:
                        skipped += 1
                        continue
                    seen.add(phone)
                    recipients.append(phone)

                if not recipients:
                    return self.send_json({"error": "None of the selected customers has a valid phone number"}, 400)

                sms_cfg = africastalking_sms_config()
                try:
                    result = send_africastalking_sms(message, recipients)
                except Exception as exc:
                    error_text = str(exc).replace(sms_cfg.get("api_key", ""), "***")
                    return self.send_json({"error": error_text[:300] or "SMS send failed"}, 502)

                sms_data = result.get("SMSMessageData", {}) if isinstance(result, dict) else {}
                provider_recipients = sms_data.get("Recipients", []) if isinstance(sms_data, dict) else []
                results = []
                sent = 0
                for item in provider_recipients:
                    status = str(item.get("status") or "")
                    status_code = item.get("statusCode")
                    if status.lower() in ("success", "sent") or status_code == 100:
                        sent += 1
                    results.append({
                        "number": item.get("number"),
                        "status": status or "Unknown",
                        "status_code": status_code,
                        "message_id": item.get("messageId") or item.get("message_id"),
                        "cost": item.get("cost"),
                    })

                self.send_json({
                    "ok": True,
                    "provider": "Africa's Talking",
                    "selected": len(customer_ids),
                    "matched": len(selected_customers),
                    "total": len(recipients),
                    "sent": sent,
                    "failed": max(0, len(recipients) - sent),
                    "skipped": skipped,
                    "message": sms_data.get("Message") if isinstance(sms_data, dict) else "",
                    "results": results,
                })
'''
if old_endpoint not in app:
    raise SystemExit('SMS send endpoint block not found')
app = app.replace(old_endpoint, new_endpoint, 1)

old_panel = '''    <div class="panel" style="margin-top:20px">
      <div class="panel-header">
        <div>
          <div class="panel-title">SMS Marketing · Africa's Talking</div>
          <div class="panel-subtitle">Live SMS sending from the POS server</div>
        </div>
        <span class="badge badge-active">DEMO MODE</span>
      </div>
      <div class="panel-body">
        <div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:end">
          <div>
            <div class="form-label">Demo recipient</div>
            <div style="font-size:16px;font-weight:800;margin-top:4px" id="promoSmsRecipient">${promoEscape(state.smsConfig?.demo_number || '+254756205063')}</div>
            <div class="promo-hint" style="margin-top:8px">For now SMS is locked to this demo Airtel number so a marketing test cannot accidentally message your saved customers. The message comes from the campaign editor above.</div>
            <div class="promo-hint" style="margin-top:5px">Provider status: <strong>${state.smsConfig?.configured ? 'Configured' : 'API key not configured on server'}</strong></div>
          </div>
          <button class="btn btn-primary" id="promoSmsSendBtn" ${state.smsConfig?.configured ? '' : 'disabled'}>Send Demo SMS</button>
        </div>
        <div id="promoSmsStatus" style="margin-top:12px"></div>
      </div>
    </div>
'''
new_panel = '''    <div class="panel" style="margin-top:20px">
      <div class="panel-header">
        <div>
          <div class="panel-title">SMS Marketing · Africa's Talking</div>
          <div class="panel-subtitle">Send the campaign above to the same customers you select for WhatsApp.</div>
        </div>
        <span class="badge badge-active">LIVE</span>
      </div>
      <div class="panel-body">
        <div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:end">
          <div>
            <div class="form-label">Selected customers</div>
            <div style="font-size:16px;font-weight:800;margin-top:4px"><span id="promoSmsSelectedCount">${state.promoSelected?.size || 0}</span> selected</div>
            <div class="promo-hint" style="margin-top:8px">SMS uses the message in the campaign editor above and the phone numbers saved on the selected customer records.</div>
            <div class="promo-hint" style="margin-top:5px">Provider status: <strong>${state.smsConfig?.configured ? 'Configured' : 'API key not configured on server'}</strong></div>
          </div>
          <button class="btn btn-primary" id="promoSmsSendBtn" ${state.smsConfig?.configured && state.promoSelected?.size ? '' : 'disabled'}>Send SMS to Selected (${state.promoSelected?.size || 0})</button>
        </div>
        <div id="promoSmsStatus" style="margin-top:12px"></div>
      </div>
    </div>
'''
if old_panel not in admin:
    raise SystemExit('SMS demo panel not found')
admin = admin.replace(old_panel, new_panel, 1)

admin = admin.replace("$('#promoSmsSendBtn')?.addEventListener('click', sendPromoSmsDemo);", "$('#promoSmsSendBtn')?.addEventListener('click', sendPromoSmsSelected);", 1)

start = admin.find('async function sendPromoSmsDemo() {')
end = admin.find('\nfunction renderPromoCustomerRows', start)
if start == -1 or end == -1:
    raise SystemExit('sendPromoSmsDemo function not found')
new_function = '''async function sendPromoSmsSelected() {
  const editor = $('#promoMessageEditor');
  const button = $('#promoSmsSendBtn');
  const status = $('#promoSmsStatus');
  const message = editor?.value?.trim() || '';
  const ids = [...(state.promoSelected || [])];

  if (!ids.length) {
    toast('Select at least one customer first.', 'info');
    return;
  }
  if (!message) {
    toast('Write a promotion message first.', 'error');
    return;
  }

  const customers = ids.map(id => state.promoCustomers.find(c => Number(c.id) === Number(id))).filter(Boolean);
  if (!confirm(`Send this SMS campaign through Africa's Talking to ${customers.length} selected customer${customers.length === 1 ? '' : 's'}?`)) return;

  const oldText = button?.textContent;
  if (button) { button.disabled = true; button.textContent = 'Sending…'; }
  if (status) status.innerHTML = `<span style="color:var(--muted)">Sending SMS to ${customers.length} customer${customers.length === 1 ? '' : 's'}…</span>`;

  try {
    const result = await api('/api/admin/sms/send', { method:'POST', body:{ message, customer_ids: ids } });
    const providerMessage = result.message ? ` · ${promoEscape(result.message)}` : '';
    const skipped = result.skipped ? ` · ${result.skipped} skipped` : '';
    if (status) status.innerHTML = `<div style="padding:10px 12px;border-radius:8px;background:#dcfce7;color:#166534;font-weight:700">✓ SMS campaign sent: ${result.sent}/${result.total} successful${skipped}${providerMessage}</div>`;
    toast(`SMS sent to ${result.sent} customer${result.sent === 1 ? '' : 's'}`);
  } catch (e) {
    if (status) status.innerHTML = `<div style="padding:10px 12px;border-radius:8px;background:#fee2e2;color:#991b1b;font-weight:700">${promoEscape(e.message)}</div>`;
    toast(e.message, 'error');
  } finally {
    updatePromoSelectionCount();
    if (button && !oldText) button.textContent = 'Send SMS to Selected';
  }
}
'''
admin = admin[:start] + new_function + admin[end:]

admin = admin.replace("${valid ? '' : ' · Invalid WhatsApp number'}", "${valid ? '' : ' · Invalid phone number'}", 1)

old_update = '''function updatePromoSelectionCount() {
  const btn = $('#promoPrepareBtn');
  if (btn) btn.textContent = `Prepare WhatsApp Messages (${state.promoSelected?.size || 0})`;
}
'''
new_update = '''function updatePromoSelectionCount() {
  const count = state.promoSelected?.size || 0;
  const btn = $('#promoPrepareBtn');
  if (btn) btn.textContent = `Prepare WhatsApp Messages (${count})`;

  const smsCount = $('#promoSmsSelectedCount');
  if (smsCount) smsCount.textContent = String(count);

  const smsBtn = $('#promoSmsSendBtn');
  if (smsBtn) {
    smsBtn.textContent = `Send SMS to Selected (${count})`;
    smsBtn.disabled = !state.smsConfig?.configured || count === 0;
  }
}
'''
if old_update not in admin:
    raise SystemExit('updatePromoSelectionCount block not found')
admin = admin.replace(old_update, new_update, 1)

app_path.write_text(app)
admin_path.write_text(admin)
print('Selected-customer SMS marketing patch applied')
