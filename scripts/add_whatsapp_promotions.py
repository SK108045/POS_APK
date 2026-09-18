from pathlib import Path

app_path = Path('app.py')
js_path = Path('static/admin.js')
css_path = Path('static/admin.css')

app = app_path.read_text()
js = js_path.read_text()
css = css_path.read_text()

customer_nav = '''        <div class="nav-item" data-section="customers">
          <span class="nav-icon">&#9646;</span>
          <span class="nav-label">Customers</span>
        </div>
'''
promo_nav = customer_nav + '''        <div class="nav-item" data-section="promotions">
          <span class="nav-icon">&#9646;</span>
          <span class="nav-label">WhatsApp Promotions</span>
        </div>
'''
if 'data-section="promotions"' not in app:
    if customer_nav not in app:
        raise SystemExit('Could not find Customers nav block in app.py')
    app = app.replace(customer_nav, promo_nav, 1)

customer_section = '      <div class="content-section" id="sec-customers"></div>\n'
promo_section = customer_section + '      <div class="content-section" id="sec-promotions"></div>\n'
if 'id="sec-promotions"' not in app:
    if customer_section not in app:
        raise SystemExit('Could not find customers content section in app.py')
    app = app.replace(customer_section, promo_section, 1)

nav_hook = "  if (section === 'customers') renderCustomers();\n"
if "section === 'promotions'" not in js:
    if nav_hook not in js:
        raise SystemExit('Could not find customer navigation hook in admin.js')
    js = js.replace(nav_hook, nav_hook + "  if (section === 'promotions') renderPromotions();\n", 1)

promo_js = r'''
// ── WHATSAPP PROMOTIONS ──────────────────────────────────────────────────────
const PROMO_PROFILE_COPY = {
  retail: {
    general: 'We have useful everyday products, fresh stock and great value waiting for you. Drop by and see what is available today.',
    stock: 'New stock has just arrived. If there is something you have been looking for, reply here and we can confirm availability.',
    offer: 'We are running a special offer for our customers. Reply here for the current deals or visit us while the offer lasts.',
    comeback: 'It has been a little while since we saw you. We would love to welcome you back and help you with your next shop.'
  },
  pharmacy: {
    general: 'We are here for your everyday pharmacy, wellness and personal-care needs. Reply here if you would like to check whether an item is available.',
    stock: 'We have received new pharmacy, wellness and personal-care stock. Reply here and we can confirm availability before you visit.',
    offer: 'We have selected in-store offers on eligible wellness and personal-care items. Reply here for details.',
    comeback: 'We have not seen you in a while. If you need to check availability of any pharmacy, wellness or personal-care item, reply here and we will assist.'
  },
  restaurant: {
    general: 'We would love to have you back for a meal. Come by for your favourites and today’s menu options.',
    stock: 'There are fresh menu options and favourites available today. Reply here if you would like to know what is on the menu.',
    offer: 'We have a special food offer available for our customers. Reply here for the details or come by and enjoy it.',
    comeback: 'We have missed serving you. Come back for a meal soon — we would be happy to have you again.'
  },
  hardware: {
    general: 'We have hardware, tools and building supplies ready for your next job. Reply here if you want us to check stock or prepare a quotation.',
    stock: 'New hardware and building-material stock has arrived. Reply with what you need and we can confirm availability or prepare a quotation.',
    offer: 'We have a special deal on selected hardware and building supplies. Reply here for pricing and availability.',
    comeback: 'Planning another project? We would be happy to help with your hardware list, stock checks and quotations.'
  },
  boutique: {
    general: 'We have fashion, beauty and cosmetics picks you may like. Come by and see what is available, or reply here for details.',
    stock: 'New arrivals are in. Reply here if you want to check sizes, colours, shades or availability before visiting.',
    offer: 'We have a special offer on selected fashion, beauty and cosmetics items. Reply here for the current deals.',
    comeback: 'We have missed you. Come see the latest arrivals, colours and styles when you get a chance.'
  },
  bar: {
    general: 'We have a great atmosphere, food and refreshments waiting for you. Come by and enjoy your next outing with us.',
    stock: 'There is something fresh happening at the venue. Reply here for today’s updates, food options and event information.',
    offer: 'We have a special venue offer available. Reply here for the details and current terms.',
    comeback: 'It has been a while since your last visit. We would be glad to welcome you back for a good time with us.'
  }
};

function promoEscape(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function normalizePromoPhone(value) {
  let digits = String(value || '').replace(/\D/g, '');
  if (!digits) return '';
  if (digits.length === 10 && digits.startsWith('0')) digits = `254${digits.slice(1)}`;
  else if (digits.length === 9 && (digits.startsWith('7') || digits.startsWith('1'))) digits = `254${digits}`;
  return digits;
}

function promoTemplateBody(type, campaign) {
  const profileCopy = PROMO_PROFILE_COPY[type] || PROMO_PROFILE_COPY.retail;
  return profileCopy[campaign] || profileCopy.general;
}

function makePromoTemplate(type, campaign, businessName) {
  const body = promoTemplateBody(type, campaign);
  return `Hi {name} 👋\n\n${businessName} here. ${body}\n\nReply to this WhatsApp if you would like more details.\n\nIf you would rather not receive promotional messages from us, reply STOP.`;
}

function personalizePromoMessage(template, customer) {
  const businessName = state.promoSettings?.business_name || 'Our business';
  return String(template || '')
    .replaceAll('{name}', customer?.name || 'there')
    .replaceAll('{business_name}', businessName);
}

async function renderPromotions() {
  const sec = $('#sec-promotions');
  sec.innerHTML = `<div class="loading-overlay"><div class="loading-spinner"></div> Loading customers…</div>`;
  try {
    const [customers, settingsPayload] = await Promise.all([
      api('/api/admin/customers'),
      api('/api/settings')
    ]);
    state.promoCustomers = (customers || []).filter(c => String(c.phone || '').trim());
    state.promoSettings = settingsPayload?.settings || {};
    state.promoProfile = settingsPayload?.profile || {};
    state.promoSelected = new Set();
    buildPromotions();
  } catch (e) {
    sec.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><p>${promoEscape(e.message)}</p></div>`;
  }
}

function buildPromotions() {
  const sec = $('#sec-promotions');
  const businessType = state.promoSettings?.business_type || 'retail';
  const businessName = state.promoSettings?.business_name || 'Our business';
  const profileName = state.promoProfile?.name || businessType;
  const initial = makePromoTemplate(businessType, 'general', businessName);

  sec.innerHTML = `
    <div class="page-header">
      <div class="page-header-left">
        <h1>WhatsApp Promotions</h1>
        <p>Customer promotions tailored for ${promoEscape(profileName)}</p>
      </div>
      <button class="btn btn-ghost btn-sm" id="promoRefreshBtn">Refresh Customers</button>
    </div>

    <div class="promo-consent-note">
      <strong>Customer privacy:</strong> only send promotions to customers who have agreed to receive marketing messages. A saved phone number alone does not necessarily mean marketing consent.
    </div>

    <div class="promo-grid">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Campaign Message</div>
            <div class="panel-subtitle">The default wording changes automatically with the active business type.</div>
          </div>
        </div>
        <div class="panel-body">
          <label class="form-label">Campaign type</label>
          <select class="form-select" id="promoCampaignType">
            <option value="general">General Promotion</option>
            <option value="stock">New Stock / New Arrivals</option>
            <option value="offer">Special Offer</option>
            <option value="comeback">We Miss You / Come Back</option>
          </select>

          <label class="form-label" style="margin-top:14px">Message</label>
          <textarea class="form-input promo-message-editor" id="promoMessageEditor">${promoEscape(initial)}</textarea>
          <div class="promo-hint">Use <code>{name}</code> for the customer's name and <code>{business_name}</code> for the business name.</div>

          <div class="promo-actions">
            <button class="btn btn-ghost" id="promoResetBtn">Reset Template</button>
            <button class="btn btn-primary" id="promoPrepareBtn">Prepare Selected Messages</button>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Customers</div>
            <div class="panel-subtitle"><span id="promoCustomerCount">${state.promoCustomers.length}</span> customers have a phone number saved</div>
          </div>
        </div>
        <div class="panel-body">
          <div class="promo-customer-toolbar">
            <input class="form-input" id="promoCustomerSearch" placeholder="Search customer or phone…">
            <label class="promo-select-all"><input type="checkbox" id="promoSelectAll"> Select all shown</label>
          </div>
          <div class="promo-customer-list" id="promoCustomerList"></div>
        </div>
      </div>
    </div>

    <div class="panel promo-queue-panel" id="promoQueuePanel" style="display:none">
      <div class="panel-header">
        <div>
          <div class="panel-title">Ready to Send</div>
          <div class="panel-subtitle">Open each chat, review the personalized message, then tap Send in WhatsApp.</div>
        </div>
      </div>
      <div class="panel-body" id="promoQueueBody"></div>
    </div>
  `;

  renderPromoCustomerRows();

  $('#promoRefreshBtn').addEventListener('click', renderPromotions);
  $('#promoCustomerSearch').addEventListener('input', e => renderPromoCustomerRows(e.target.value));
  $('#promoCampaignType').addEventListener('change', resetPromoTemplate);
  $('#promoResetBtn').addEventListener('click', resetPromoTemplate);
  $('#promoPrepareBtn').addEventListener('click', preparePromoQueue);
  $('#promoSelectAll').addEventListener('change', e => {
    $$('.promo-customer-check').forEach(cb => {
      cb.checked = e.target.checked;
      const id = Number(cb.value);
      if (cb.checked) state.promoSelected.add(id);
      else state.promoSelected.delete(id);
    });
    updatePromoSelectionCount();
  });
}

function resetPromoTemplate() {
  const type = state.promoSettings?.business_type || 'retail';
  const businessName = state.promoSettings?.business_name || 'Our business';
  const campaign = $('#promoCampaignType')?.value || 'general';
  const editor = $('#promoMessageEditor');
  if (editor) editor.value = makePromoTemplate(type, campaign, businessName);
}

function renderPromoCustomerRows(filter = '') {
  const root = $('#promoCustomerList');
  if (!root) return;
  const q = String(filter || '').trim().toLowerCase();
  const rows = state.promoCustomers.filter(c =>
    !q || String(c.name || '').toLowerCase().includes(q) || String(c.phone || '').toLowerCase().includes(q)
  );

  root.innerHTML = rows.length ? rows.map(c => {
    const valid = normalizePromoPhone(c.phone).length >= 10;
    const checked = state.promoSelected.has(Number(c.id));
    return `
      <label class="promo-customer-row ${valid ? '' : 'invalid'}">
        <input type="checkbox" class="promo-customer-check" value="${Number(c.id)}" ${checked ? 'checked' : ''} ${valid ? '' : 'disabled'}>
        <div class="promo-customer-info">
          <strong>${promoEscape(c.name || 'Unnamed customer')}</strong>
          <span>${promoEscape(c.phone || '')}${valid ? '' : ' · Invalid WhatsApp number'}</span>
        </div>
      </label>`;
  }).join('') : `<div class="empty-state"><p>No customers with phone numbers match your search.</p></div>`;

  $$('.promo-customer-check', root).forEach(cb => cb.addEventListener('change', () => {
    const id = Number(cb.value);
    if (cb.checked) state.promoSelected.add(id);
    else state.promoSelected.delete(id);
    updatePromoSelectionCount();
  }));

  updatePromoSelectionCount();
}

function updatePromoSelectionCount() {
  const btn = $('#promoPrepareBtn');
  if (btn) btn.textContent = `Prepare Selected Messages (${state.promoSelected?.size || 0})`;
}

function preparePromoQueue() {
  const ids = [...(state.promoSelected || [])];
  if (!ids.length) {
    toast('Select at least one customer first.', 'info');
    return;
  }

  if (!confirm('Send only to customers who agreed to receive promotional WhatsApp messages. Continue preparing this campaign?')) return;

  const template = $('#promoMessageEditor')?.value?.trim();
  if (!template) {
    toast('Write a promotion message first.', 'error');
    return;
  }

  const customers = ids.map(id => state.promoCustomers.find(c => Number(c.id) === Number(id))).filter(Boolean);
  const queue = $('#promoQueuePanel');
  const body = $('#promoQueueBody');
  queue.style.display = 'block';
  body.innerHTML = customers.map(c => `
    <div class="promo-queue-row">
      <div>
        <strong>${promoEscape(c.name || 'Customer')}</strong>
        <div class="promo-queue-phone">${promoEscape(c.phone)}</div>
      </div>
      <button class="btn btn-primary btn-sm" data-promo-open="${Number(c.id)}">Open WhatsApp</button>
    </div>
  `).join('');

  $$('[data-promo-open]', body).forEach(btn => btn.addEventListener('click', () => openPromoWhatsApp(Number(btn.dataset.promoOpen))));
  queue.scrollIntoView({behavior: 'smooth', block: 'start'});
}

function openPromoWhatsApp(customerId) {
  const customer = state.promoCustomers.find(c => Number(c.id) === Number(customerId));
  if (!customer) return;
  const phone = normalizePromoPhone(customer.phone);
  if (phone.length < 10 || phone.length > 15) {
    toast(`Invalid WhatsApp number for ${customer.name || 'customer'}.`, 'error');
    return;
  }
  const template = $('#promoMessageEditor')?.value || '';
  const message = personalizePromoMessage(template, customer);
  const url = `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
  window.open(url, '_blank', 'noopener,noreferrer');
}

'''

boot_marker = '// ── BOOT ──'
if 'const PROMO_PROFILE_COPY' not in js:
    if boot_marker not in js:
        raise SystemExit('Could not find BOOT marker in admin.js')
    js = js.replace(boot_marker, promo_js + '\n' + boot_marker, 1)

promo_css = r'''

/* ── WhatsApp Promotions ─────────────────────────────────────────────────── */
.promo-consent-note {
  margin-bottom: 18px;
  padding: 12px 14px;
  border: 1px solid #fde68a;
  background: #fffbeb;
  color: #854d0e;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
}
.promo-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, .9fr);
  gap: 18px;
  align-items: start;
  margin-bottom: 18px;
}
.promo-message-editor { min-height: 230px; resize: vertical; line-height: 1.55; white-space: pre-wrap; }
.promo-hint { margin-top: 8px; color: var(--muted); font-size: 12px; line-height: 1.45; }
.promo-hint code { background: var(--bg); border: 1px solid var(--line); border-radius: 4px; padding: 1px 5px; }
.promo-actions { display: flex; justify-content: space-between; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
.promo-customer-toolbar { display: grid; gap: 10px; margin-bottom: 12px; }
.promo-select-all { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; font-weight: 700; }
.promo-customer-list { max-height: 430px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
.promo-customer-row { display: flex; align-items: center; gap: 12px; padding: 11px 12px; border-bottom: 1px solid var(--line); cursor: pointer; }
.promo-customer-row:last-child { border-bottom: 0; }
.promo-customer-row:hover { background: var(--bg); }
.promo-customer-row.invalid { opacity: .55; cursor: not-allowed; }
.promo-customer-row input { width: 16px; height: 16px; }
.promo-customer-info { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.promo-customer-info strong { font-size: 13px; }
.promo-customer-info span { color: var(--muted); font-size: 12px; }
.promo-queue-panel { margin-bottom: 24px; }
.promo-queue-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 0; border-bottom: 1px solid var(--line); }
.promo-queue-row:last-child { border-bottom: 0; }
.promo-queue-phone { color: var(--muted); font-size: 12px; margin-top: 3px; }
@media (max-width: 900px) { .promo-grid { grid-template-columns: 1fr; } }
'''

if '/* ── WhatsApp Promotions' not in css:
    css += promo_css

app_path.write_text(app)
js_path.write_text(js)
css_path.write_text(css)
