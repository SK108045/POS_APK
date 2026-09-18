(() => {
  const q = (s, root = document) => root.querySelector(s);
  const qa = (s, root = document) => [...root.querySelectorAll(s)];

  const COPY = {
    retail: {
      general: 'We have fresh stock, everyday essentials and great value waiting for you. Drop by and see what is available today.',
      stock: 'New stock has just arrived. Reply here if you want us to confirm availability before you visit.',
      offer: 'We have a special offer for our customers. Reply here for the current deals while the offer lasts.',
      comeback: 'It has been a while since we saw you. We would love to welcome you back for your next shop.'
    },
    pharmacy: {
      general: 'We are here for your everyday pharmacy, wellness and personal-care needs. Reply if you want us to check availability of an item.',
      stock: 'New pharmacy, wellness and personal-care stock has arrived. Reply here and we can confirm availability before you visit.',
      offer: 'We have selected offers on eligible wellness and personal-care items. Reply here for details.',
      comeback: 'We have not seen you in a while. Reply if you need us to check availability of any pharmacy or wellness item.'
    },
    restaurant: {
      general: 'We would love to have you back for a meal. Come by for your favourites and today’s menu options.',
      stock: 'Fresh menu options and customer favourites are available today. Reply here if you would like to know what is on the menu.',
      offer: 'We have a special food offer available. Reply here for the details or come by and enjoy it.',
      comeback: 'We have missed serving you. Come back for a meal soon — we would be happy to have you again.'
    },
    hardware: {
      general: 'We have hardware, tools and building supplies ready for your next job. Reply if you want a stock check or quotation.',
      stock: 'New hardware and building-material stock has arrived. Reply with what you need and we can confirm availability or prepare a quotation.',
      offer: 'We have a special deal on selected hardware and building supplies. Reply here for pricing and availability.',
      comeback: 'Planning another project? We would be happy to help with your hardware list, stock checks and quotations.'
    },
    boutique: {
      general: 'We have fashion, beauty and cosmetics picks you may like. Come by and see what is available, or reply here for details.',
      stock: 'New arrivals are in. Reply if you want to check sizes, colours, shades or availability before visiting.',
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

  let customers = [];
  let settings = {};
  let profile = {};
  let selected = new Set();
  let loaded = false;

  function escapeHtml(v) {
    return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function phone(v) {
    let d = String(v || '').replace(/\D/g, '');
    if (d.length === 10 && d.startsWith('0')) d = `254${d.slice(1)}`;
    else if (d.length === 9 && (d.startsWith('7') || d.startsWith('1'))) d = `254${d}`;
    return d;
  }

  async function getJson(url) {
    const r = await fetch(url, {headers: {'Accept':'application/json'}});
    if (r.status === 401 || r.status === 403) {
      location.href = '/admin';
      throw new Error('Session expired');
    }
    if (!r.ok) throw new Error(`Request failed (${r.status})`);
    return r.json();
  }

  function template(kind) {
    const type = settings.business_type || 'retail';
    const business = settings.business_name || 'Our business';
    const copy = COPY[type] || COPY.retail;
    return `Hi {name} 👋\n\n${business} here. ${copy[kind] || copy.general}\n\nReply to this WhatsApp if you would like more details.\n\nReply STOP if you do not want promotional messages from us.`;
  }

  function renderRows(filter = '') {
    const root = q('#promoCustomerList');
    if (!root) return;
    const term = String(filter).trim().toLowerCase();
    const rows = customers.filter(c => !term || String(c.name || '').toLowerCase().includes(term) || String(c.phone || '').toLowerCase().includes(term));
    root.innerHTML = rows.length ? rows.map(c => {
      const ok = phone(c.phone).length >= 10;
      return `<label class="promo-customer-row ${ok ? '' : 'invalid'}">
        <input class="promo-check" type="checkbox" value="${Number(c.id)}" ${selected.has(Number(c.id)) ? 'checked' : ''} ${ok ? '' : 'disabled'}>
        <span><strong>${escapeHtml(c.name || 'Unnamed customer')}</strong><small>${escapeHtml(c.phone || '')}${ok ? '' : ' · Invalid number'}</small></span>
      </label>`;
    }).join('') : '<div class="promo-empty">No matching customers with phone numbers.</div>';
    qa('.promo-check', root).forEach(el => el.addEventListener('change', () => {
      const id = Number(el.value);
      el.checked ? selected.add(id) : selected.delete(id);
      updateCount();
    }));
    updateCount();
  }

  function updateCount() {
    const b = q('#promoPrepare');
    if (b) b.textContent = `Prepare Selected (${selected.size})`;
  }

  function personalize(text, c) {
    return String(text || '')
      .split('{name}').join(c.name || 'there')
      .split('{business_name}').join(settings.business_name || 'Our business');
  }

  function prepare() {
    if (!selected.size) return alert('Select at least one customer first.');
    const editor = q('#promoMessage');
    const text = editor ? editor.value.trim() : '';
    if (!text) return alert('Write a promotional message first.');
    const list = [...selected].map(id => customers.find(c => Number(c.id) === id)).filter(Boolean);
    const out = q('#promoQueue');
    out.innerHTML = `<div class="promo-queue-title">Ready to send</div>${list.map(c => `<div class="promo-queue-row">
      <span><strong>${escapeHtml(c.name || 'Customer')}</strong><small>${escapeHtml(c.phone || '')}</small></span>
      <button type="button" class="promo-open" data-id="${Number(c.id)}">Open WhatsApp</button>
    </div>`).join('')}`;
    qa('.promo-open', out).forEach(btn => btn.addEventListener('click', () => {
      const c = customers.find(x => Number(x.id) === Number(btn.dataset.id));
      if (!c) return;
      const p = phone(c.phone);
      if (p.length < 10 || p.length > 15) return alert('Invalid WhatsApp number.');
      window.open(`https://wa.me/${p}?text=${encodeURIComponent(personalize(text, c))}`, '_blank', 'noopener,noreferrer');
    }));
    out.scrollIntoView({behavior:'smooth', block:'start'});
  }

  function build() {
    const sec = q('#sec-promotions');
    if (!sec) return;
    const type = settings.business_type || 'retail';
    const profileName = profile.name || type;
    sec.innerHTML = `<div class="page-header"><div class="page-header-left"><h1>WhatsApp Promotions</h1><p>Business-specific customer campaigns for ${escapeHtml(profileName)}</p></div><button class="btn btn-ghost btn-sm" id="promoReload">Refresh</button></div>
      <div class="promo-note"><strong>Marketing consent:</strong> only send promotions to customers who agreed to receive them.</div>
      <div class="promo-layout">
        <div class="panel"><div class="panel-header"><div><div class="panel-title">Campaign Message</div><div class="panel-subtitle">The default wording follows the current business type.</div></div></div><div class="panel-body">
          <label class="form-label">Campaign type</label>
          <select id="promoKind" class="form-select"><option value="general">General Promotion</option><option value="stock">New Stock / New Arrivals</option><option value="offer">Special Offer</option><option value="comeback">We Miss You / Come Back</option></select>
          <label class="form-label promo-label">Message</label>
          <textarea id="promoMessage" class="form-input promo-editor">${escapeHtml(template('general'))}</textarea>
          <div class="promo-hint">Use <code>{name}</code> for the customer name.</div>
          <div class="promo-buttons"><button class="btn btn-ghost" id="promoReset">Reset Template</button><button class="btn btn-primary" id="promoPrepare">Prepare Selected (0)</button></div>
        </div></div>
        <div class="panel"><div class="panel-header"><div><div class="panel-title">Customers</div><div class="panel-subtitle">${customers.length} customers have a phone number saved</div></div></div><div class="panel-body">
          <input id="promoSearch" class="form-input" placeholder="Search customer or phone…">
          <label class="promo-all"><input id="promoAll" type="checkbox"> Select all shown</label>
          <div id="promoCustomerList" class="promo-customer-list"></div>
        </div></div>
      </div><div id="promoQueue" class="panel promo-queue"></div>`;

    renderRows();
    q('#promoSearch').addEventListener('input', e => renderRows(e.target.value));
    q('#promoKind').addEventListener('change', e => { q('#promoMessage').value = template(e.target.value); });
    q('#promoReset').addEventListener('click', () => { q('#promoMessage').value = template(q('#promoKind').value); });
    q('#promoPrepare').addEventListener('click', prepare);
    q('#promoReload').addEventListener('click', () => load(true));
    q('#promoAll').addEventListener('change', e => {
      qa('.promo-check').forEach(cb => { if (!cb.disabled) { cb.checked = e.target.checked; e.target.checked ? selected.add(Number(cb.value)) : selected.delete(Number(cb.value)); } });
      updateCount();
    });
  }

  async function load(force = false) {
    const sec = q('#sec-promotions');
    if (!sec) return;
    if (loaded && !force) return build();
    sec.innerHTML = '<div class="loading-overlay"><div class="loading-spinner"></div> Loading customers…</div>';
    try {
      const [cs, sp] = await Promise.all([getJson('/api/admin/customers'), getJson('/api/settings')]);
      customers = (cs || []).filter(c => String(c.phone || '').trim());
      settings = sp.settings || {};
      profile = sp.profile || {};
      selected = new Set();
      loaded = true;
      build();
    } catch (e) {
      sec.innerHTML = `<div class="promo-error">Could not load promotions: ${escapeHtml(e.message)}</div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const nav = q('.nav-item[data-section="promotions"]');
    if (!nav) return;
    nav.addEventListener('click', () => load());
  });
})();
