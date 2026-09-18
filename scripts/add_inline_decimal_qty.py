from pathlib import Path
p = Path('static/app.js')
s = p.read_text()
old = '''            <button data-qty="${Math.max(0, (item.qty - 1))}" data-id="${item.id}">−</button>
            <strong>${item.qty}</strong>
            <button data-qty="${item.qty + 1}" data-id="${item.id}">+</button>
'''
new = '''            <button data-qty="${Math.max(0, (item.qty - 1))}" data-id="${item.id}">−</button>
            ${(dbItem.decimal_qty_enabled || hasCap('decimal_qty'))
              ? `<input type="number" class="cart-qty-input" data-id="${item.id}" value="${item.qty}" min="0.01" step="0.01" inputmode="decimal" style="width:64px;text-align:center;padding:4px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);font-weight:700;">`
              : `<strong>${item.qty}</strong>`}
            <button data-qty="${item.qty + 1}" data-id="${item.id}">+</button>
'''
if old not in s:
    raise SystemExit('cart quantity markup not found')
s = s.replace(old, new, 1)
old2 = '''  qsa('.qty-controls button').forEach(btn =>
    btn.addEventListener('click', () => changeQty(Number(btn.dataset.id), Number(btn.dataset.qty)))
  );

  foot.innerHTML = `
'''
new2 = '''  qsa('.qty-controls button').forEach(btn =>
    btn.addEventListener('click', () => changeQty(Number(btn.dataset.id), Number(btn.dataset.qty)))
  );
  qsa('.cart-qty-input').forEach(input => {
    const applyQty = () => {
      const qty = Number.parseFloat(input.value);
      if (!Number.isFinite(qty) || qty <= 0) {
        toast('Enter a quantity greater than 0', 'error');
        renderTicket();
        return;
      }
      changeQty(Number(input.dataset.id), Math.round(qty * 100) / 100);
    };
    input.addEventListener('change', applyQty);
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        input.blur();
      }
    });
  });

  foot.innerHTML = `
'''
if old2 not in s:
    raise SystemExit('cart quantity listener marker not found')
s = s.replace(old2, new2, 1)
p.write_text(s)
