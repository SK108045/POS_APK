from pathlib import Path
import subprocess

subprocess.run(['python3', 'scripts/add_africastalking_sms.py'], check=True)

p = Path('static/admin.js')
s = p.read_text()
bad = '''  if (status) status.innerHTML = '<span style="color:var(--muted)">Sending through Africa's Talking…</span>';'''
good = '''  if (status) status.innerHTML = `<span style="color:var(--muted)">Sending through Africa's Talking…</span>`;'''
if bad not in s:
    raise SystemExit('expected Africa\'s Talking status string not found')
s = s.replace(bad, good, 1)
p.write_text(s)
