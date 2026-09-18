from pathlib import Path

path = Path('scripts/scope_business_workspaces.py')
s = path.read_text()
start_marker = "    if not block.endswith('\\\"\\\"\\\"'):"
# Actual source contains literal triple quotes inside the string expression.
start_marker = "    if not block.endswith('\"\"\"'):"
end_marker = "    py = py[:start] + block + py[end:]"
start = s.find(start_marker)
end = s.find(end_marker, start)
if start == -1 or end == -1:
    raise SystemExit(f'Could not locate guard block: start={start} end={end}')
replacement = '''    quote_pos = block.rfind('"""')
    if quote_pos == -1:
        raise SystemExit('Could not locate hidden_admin_page closing quotes')
    replacement_tail = '"""\\n    return (html\\n            .replace("__SHOP_ICON__", profile.get("icon", "🏪"))\\n            .replace("__SHOP_NAME__", profile.get("name", business_type)))'
    block = block[:quote_pos] + replacement_tail + block[quote_pos + 3:]
'''
s = s[:start] + replacement + s[end:]
path.write_text(s)
