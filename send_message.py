def send_text():
    """Send the WhatsApp message through Whapi with one mention."""
    url = f"{API_BASE}/messages/text"
    headers = {
        "Authorization": f"Bearer {WHAPI_TOKEN}",
        "Content-Type": "application/json"
    }

    # ✅ Proper message format for mention
    body_text = "please confirm if rent for Raintree flat has been received this month? @user"

    payload = {
        "to": GROUP_ID,
        "body": body_text,
        "mentions": [MENTION_WAID]   # e.g., "918483826996"
    }

    print(f"[send] Sending to {GROUP_ID}...")
    print(f"[debug] Payload: {payload}")  # Optional for log clarity

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"[http] {r.status_code} {r.text}")

    if r.status_code != 200:
        fail("Whapi rejected the request. Check token, group ID, or mention format.")

    try:
        resp = r.json()
    except Exception:
        fail("Non-JSON response from API.")

    return (((resp or {}).get("message")) or {}).get("id")
