from pathlib import Path

p = Path('app.py')
s = p.read_text()
old = '    return africastalking.SMS.send(message, recipients, timeout=30)\n'
new = '    return africastalking.SMS.send(message, recipients)\n'
if old not in s:
    raise SystemExit('Expected Africa\'s Talking send call not found')
s = s.replace(old, new, 1)
p.write_text(s)
