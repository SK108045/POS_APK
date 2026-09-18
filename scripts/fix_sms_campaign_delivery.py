from pathlib import Path

app_path = Path('app.py')
admin_path = Path('static/admin.js')

app = app_path.read_text()
admin = admin_path.read_text()

# Match the exact Africa's Talking send signature already proven to work.
app = app.replace(
    '    return africastalking.SMS.send(message, recipients)\n',
    '    return africastalking.SMS.send(message, recipients, timeout=30)\n',
    1,
)

# Add robust SMS phone normalization helper.
anchor = '''def normalize_customer_phone(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if not digits:
        return ''
    if len(digits) == 10 and digits.startswith('0'):
        digits = '254' + digits[1:]
    elif len(digits) == 9 and digits[0] in ('7', '1'):
        digits = '254' + digits
    return digits


'''
helper = anchor + '''def normalize_sms_phone(value):
    """Return an E.164-style phone number for Africa's Talking."""
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if not digits:
        return ''

    # Handle common Kenyan formats: 07..., 7..., 2547..., +2547...
    # and the occasionally saved +25407... form.
    if digits.startswith('00254'):
        digits = digits[2:]
    if digits.startswith('2540') and len(digits) == 13:
        digits = '254' + digits[4:]
    elif len(digits) == 10 and digits.startswith('0'):
        digits = '254' + digits[1:]
    elif len(digits) == 9 and digits[0] in ('7', '1'):
        digits = '254' + digits

    if len(digits) < 10 or len(digits) > 15:
        return ''
    return '+' + digits


'''
if 'def normalize_sms_phone(value):' not in app:
    if anchor not in app:
        raise SystemExit('normalize_customer_phone anchor not found')
    app = app.replace(anchor, helper, 1)

start = app.index('            elif path == "/api/admin/sms/send":')
end = app.index('            elif path == "/api/stock/adjust":', start)
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

                sms_cfg = africastalking_sms_config()
                seen = set()
                results = []
                skipped = 0
                sent = 0

                # Send each customer separately. This mirrors the single-recipient call
                # already verified against this Africa's Talking account and lets one
                # bad number fail without hiding/blocking every other recipient.
                for customer in selected_customers:
                    phone = normalize_sms_phone(customer.get("phone"))
                    if not phone or phone in seen:
                        skipped += 1
                        results.append({
                            "customer_id": customer.get("id"),
                            "customer_name": customer.get("name") or "Customer",
                            "number": phone or str(customer.get("phone") or ""),
                            "status": "Skipped - invalid or duplicate phone number",
                            "status_code": None,
                            "message_id": None,
                            "cost": None,
                            "success": False,
                        })
                        continue
                    seen.add(phone)

                    try:
                        provider_result = send_africastalking_sms(message, [phone])
                    except Exception as exc:
                        error_text = str(exc).replace(sms_cfg.get("api_key", ""), "***")[:300]
                        results.append({
                            "customer_id": customer.get("id"),
                            "customer_name": customer.get("name") or "Customer",
                            "number": phone,
                            "status": error_text or "SMS send failed",
                            "status_code": None,
                            "message_id": None,
                            "cost": None,
                            "success": False,
                        })
                        continue

                    sms_data = provider_result.get("SMSMessageData", {}) if isinstance(provider_result, dict) else {}
                    provider_recipients = sms_data.get("Recipients", []) if isinstance(sms_data, dict) else []
                    item = provider_recipients[0] if provider_recipients else {}
                    status = str(item.get("status") or sms_data.get("Message") or "Unknown")
                    status_code = item.get("statusCode")
                    success = status.lower() in ("success", "sent") or status_code == 100
                    if success:
                        sent += 1

                    results.append({
                        "customer_id": customer.get("id"),
                        "customer_name": customer.get("name") or "Customer",
                        "number": item.get("number") or phone,
                        "status": status,
                        "status_code": status_code,
                        "message_id": item.get("messageId") or item.get("message_id"),
                        "cost": item.get("cost"),
                        "success": success,
                        "provider_message": sms_data.get("Message") if isinstance(sms_data, dict) else "",
                    })

                attempted = len([r for r in results if not str(r.get("status", "")).startswith("Skipped")])
                failed = max(0, attempted - sent)
                self.send_json({
                    "ok": sent > 0,
                    "provider": "Africa's Talking",
                    "selected": len(customer_ids),
                    "matched": len(selected_customers),
                    "total": attempted,
                    "sent": sent,
                    "failed": failed,
                    "skipped": skipped,
                    "results": results,
                })
'''
app = app[:start] + new_endpoint + app[end:]

old_front = '''    const result = await api('/api/admin/sms/send', { method:'POST', body:{ message, customer_ids: ids } });
    const providerMessage = result.message ? ` · ${promoEscape(result.message)}` : '';
    const skipped = result.skipped ? ` · ${result.skipped} skipped` : '';
    if (status) status.innerHTML = `<div style="padding:10px 12px;border-radius:8px;background:#dcfce7;color:#166534;font-weight:700">✓ SMS campaign sent: ${result.sent}/${result.total} successful${skipped}${providerMessage}</div>`;
    toast(`SMS sent to ${result.sent} customer${result.sent === 1 ? '' : 's'}`);
'''
new_front = '''    const result = await api('/api/admin/sms/send', { method:'POST', body:{ message, customer_ids: ids } });
    const skipped = result.skipped ? ` · ${result.skipped} skipped` : '';
    const allGood = result.sent > 0 && result.failed === 0;
    const anyGood = result.sent > 0;
    const bg = allGood ? '#dcfce7' : (anyGood ? '#fef3c7' : '#fee2e2');
    const fg = allGood ? '#166534' : (anyGood ? '#92400e' : '#991b1b');
    const icon = allGood ? '✓' : (anyGood ? '⚠' : '✕');
    const detailRows = (result.results || []).map(r => {
      const code = r.status_code != null ? ` · code ${promoEscape(r.status_code)}` : '';
      const cost = r.cost ? ` · ${promoEscape(r.cost)}` : '';
      const name = r.customer_name ? `${promoEscape(r.customer_name)} · ` : '';
      return `<div style="margin-top:6px;font-weight:600">${r.success ? '✓' : '✕'} ${name}${promoEscape(r.number || '')} — ${promoEscape(r.status || 'Unknown')}${code}${cost}</div>`;
    }).join('');
    if (status) status.innerHTML = `<div style="padding:10px 12px;border-radius:8px;background:${bg};color:${fg};font-weight:700">${icon} SMS campaign: ${result.sent}/${result.total} successful${skipped}${detailRows}</div>`;
    if (result.sent > 0) toast(`SMS sent to ${result.sent} customer${result.sent === 1 ? '' : 's'}`);
    else toast('No SMS messages were sent. Check the provider status shown below.', 'error');
'''
if old_front not in admin:
    raise SystemExit('frontend SMS result block not found')
admin = admin.replace(old_front, new_front, 1)

app_path.write_text(app)
admin_path.write_text(admin)
