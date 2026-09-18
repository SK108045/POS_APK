from pathlib import Path

p = Path('static/app.js')
s = p.read_text()

marker = "function updateHeaderAndNav() {\n"
if marker not in s:
    raise SystemExit('updateHeaderAndNav marker not found')

helper = r'''function syncActiveTopNav(path = window.location.pathname) {
  const navRoot = qs('#topNav') || qs('header nav');
  if (!navRoot) return;
  const currentPath = (path || '/pos').replace(/\/+$/, '') || '/pos';
  qsa('.nav-link', navRoot).forEach(link => {
    const linkPath = new URL(link.href, window.location.origin).pathname.replace(/\/+$/, '') || '/';
    const active = linkPath === currentPath;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
}

'''

if 'function syncActiveTopNav(' not in s:
    s = s.replace(marker, helper + marker, 1)

old = r'''    const currentPath = (window.location.pathname || '/pos').replace(/\/+$/, '') || '/pos';
    navRoot.innerHTML = navItems.map(item => {
      const itemPath = item.href.replace(/\/+$/, '') || '/';
      const isActive = itemPath === currentPath;
      return `<a class="nav-link ${isActive ? 'active' : ''}" href="${item.href}" ${isActive ? 'aria-current="page"' : ''}><span class="nav-icon">${item.icon}</span>${item.label}</a>`;
    }).join('');
'''
new = r'''    navRoot.innerHTML = navItems.map(item =>
      `<a class="nav-link" href="${item.href}"><span class="nav-icon">${item.icon}</span>${item.label}</a>`
    ).join('');
    syncActiveTopNav();
'''
if old not in s:
    raise SystemExit('existing nav route block not found')
s = s.replace(old, new, 1)

# Add router synchronization once, after the header function block and before api().
anchor = "\nasync function api(path, options = {}) {\n"
router_hook = r'''
if (!window.__posActiveNavRouterHooked) {
  window.__posActiveNavRouterHooked = true;
  const originalPushState = history.pushState.bind(history);
  const originalReplaceState = history.replaceState.bind(history);

  history.pushState = (...args) => {
    const result = originalPushState(...args);
    queueMicrotask(() => syncActiveTopNav());
    return result;
  };

  history.replaceState = (...args) => {
    const result = originalReplaceState(...args);
    queueMicrotask(() => syncActiveTopNav());
    return result;
  };

  window.addEventListener('popstate', () => queueMicrotask(() => syncActiveTopNav()));
  document.addEventListener('click', event => {
    const link = event.target.closest?.('#topNav .nav-link, header nav .nav-link');
    if (!link) return;
    const path = new URL(link.href, window.location.origin).pathname;
    syncActiveTopNav(path);
  });
}
'''

if 'window.__posActiveNavRouterHooked' not in s:
    if anchor not in s:
        raise SystemExit('api anchor not found')
    s = s.replace(anchor, router_hook + anchor, 1)

p.write_text(s)
