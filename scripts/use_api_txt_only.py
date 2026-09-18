from pathlib import Path

p = Path('app.py')
s = p.read_text()
old = '''def africastalking_sms_config():
    """Return SMS configuration without ever exposing the API key to the browser."""
    import os

    username = os.environ.get("AFRICASTALKING_USERNAME", "sk10").strip() or "sk10"
    api_key = os.environ.get("AFRICASTALKING_API_KEY", "").strip()
    if not api_key:
        key_file = BASE_DIR / "api.txt"
        if key_file.exists():
            api_key = key_file.read_text(encoding="utf-8").strip()

    demo_number = os.environ.get("AFRICASTALKING_DEMO_NUMBER", "+254756205063").strip() or "+254756205063"
    return {
        "username": username,
        "api_key": api_key,
        "demo_number": demo_number,
        "configured": bool(username and api_key),
    }
'''
new = '''def africastalking_sms_config():
    """Load Africa's Talking credentials directly from this repo's api.txt file."""
    username = "sk10"
    key_file = BASE_DIR / "api.txt"
    api_key = key_file.read_text(encoding="utf-8").strip() if key_file.exists() else ""
    demo_number = "+254756205063"
    return {
        "username": username,
        "api_key": api_key,
        "demo_number": demo_number,
        "configured": bool(api_key),
    }
'''
if old not in s:
    raise SystemExit('africastalking_sms_config block not found')
s = s.replace(old, new, 1)
p.write_text(s)
