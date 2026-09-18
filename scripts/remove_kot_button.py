from pathlib import Path

p = Path('static/app.js')
s = p.read_text()

old_button = '''          <button class="primary" id="checkoutBtn" style="flex:1;">Checkout</button>\n          ${hasCap('kot') ? `<button class="secondary" id="kotBtn" style="flex:1; background:#fef3c7; color:#92400e; border:1px solid #fde68a;">🍳 Send KOT</button>` : ''}\n'''
new_button = '''          <button class="primary" id="checkoutBtn" style="flex:1;">Checkout</button>\n'''

if old_button not in s:
    raise SystemExit('KOT button block not found')
s = s.replace(old_button, new_button, 1)

old_handler = '''    if (hasCap('kot')) {\n      qs('#kotBtn')?.addEventListener('click', async () => {\n        try {\n          await api('/api/order/kot', { method: 'POST', body: { order_id: state.order.id } });\n          toast('Order sent to kitchen / bar KOT!', 'success');\n          showReceiptModal(state.order, true);\n        } catch(err) {\n          toast(err.message, 'error');\n        }\n      });\n    }\n'''

if old_handler not in s:
    raise SystemExit('KOT click handler not found')
s = s.replace(old_handler, '', 1)

p.write_text(s)
