from pathlib import Path

app_path = Path('static/app.js')
css_path = Path('static/styles.css')

app = app_path.read_text()
css = css_path.read_text()

old_nav = '''    const activeLabel = pageName() ? (SPA_PAGES['/' + pageName()]?.active || 'POS') : 'POS';\n    navRoot.innerHTML = navItems.map(item =>\n      `<a class="nav-link ${activeLabel === item.label ? 'active' : ''}" href="${item.href}"><span class="nav-icon">${item.icon}</span>${item.label}</a>`\n    ).join('');\n'''
new_nav = '''    const currentPath = (window.location.pathname || '/pos').replace(/\\/+$/, '') || '/pos';\n    navRoot.innerHTML = navItems.map(item => {\n      const itemPath = item.href.replace(/\\/+$/, '') || '/';\n      const isActive = itemPath === currentPath;\n      return `<a class="nav-link ${isActive ? 'active' : ''}" href="${item.href}" ${isActive ? 'aria-current="page"' : ''}><span class="nav-icon">${item.icon}</span>${item.label}</a>`;\n    }).join('');\n'''
if old_nav not in app:
    raise SystemExit('nav active-state block not found')
app = app.replace(old_nav, new_nav, 1)

old_css = '''.nav-link.active {\n  background: #18181b;\n  color: #ffffff !important;\n  font-weight: 700;\n}\n\n[data-theme="dark"] .nav-link {\n  color: var(--muted);\n}\n[data-theme="dark"] .nav-link:hover {\n  background: var(--line);\n  color: var(--ink);\n}\n[data-theme="dark"] .nav-link.active {\n  background: #27272a;\n  color: #ffffff !important;\n  box-shadow: inset 0 0 0 1px #3f3f46;\n}\n'''
new_css = '''.nav-link.active {\n  background: #e4e4e7;\n  color: #18181b !important;\n  font-weight: 800;\n  box-shadow: inset 0 0 0 1px #d4d4d8;\n}\n\n[data-theme="dark"] .nav-link {\n  color: var(--muted);\n}\n[data-theme="dark"] .nav-link:hover {\n  background: var(--line);\n  color: var(--ink);\n}\n[data-theme="dark"] .nav-link.active {\n  background: #3f3f46;\n  color: #fafafa !important;\n  box-shadow: inset 0 0 0 1px #52525b;\n}\n'''
if old_css not in css:
    raise SystemExit('nav active CSS block not found')
css = css.replace(old_css, new_css, 1)

app_path.write_text(app)
css_path.write_text(css)
