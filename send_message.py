import os, sys, time, requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Load environment variables if running locally
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# === Schedule (IST-based) ===
IST_DAY  = os.getenv("IST_DAY",  "03")      # Day of the month (e.g., "03")
IST_TIME = os.getenv("IST_TIME", "13:36")   # Target time in IST (24h format)
TZ_NAME  = os.getenv("TIMEZONE", "Asia/Kolkata")

# === Whapi Configuration ===
WHAPI_TOKEN  = os.getenv("WHAPI_TOKEN", "").strip()
GROUP_ID     = os.getenv("GROUP_ID", "").strip()
MENTION_WAID = os.getenv("MENTION_WAID", "").strip()

# === Message Content ===
DISPLAY_NAME = os.getenv("DISPLAY_NAME", "Sanket").strip()
MESSAGE      = os.getenv("MESSAGE", "📩 Rent check: Have you received the *Raintree* flat rent this month?").strip()

API_BASE = "https://gate.whapi.cloud"


# === Helper Functions ===
def fail(msg: str):
    print(f"[error] {msg}")
    sys.exit(1)


def validate():
    """Check that all required environment variables are provided."""
    missing = [k for k, v in {
        "WHAPI_TOKEN": WHAPI_TOKEN,
        "GROUP_ID": GROUP_ID,
        "MENTION_WAID": MENTION_WAID,
    }.items() if not v]

    if missing:
        fail(f"Missing env vars: {', '.join(missing)}")

    if not GROUP_ID.endswith("@g.us"):
        fail("GROUP_ID must end with @g.us (e.g., 1203…@g.us).")

    if not MENTION_WAID.isdigit():
        fail("MENTION_WAID must be digits only (international format, no '+').")


def ist_gate():
    """Allow sending within ±5 minutes of the scheduled IST_TIME on IST_DAY."""
    try:
        tz = ZoneInfo(TZ_NAME)
    except Exception:
        fail(f"Invalid TIMEZONE: {TZ_NAME}")

    now = datetime.now(tz)
    current_day = int(now.strftime("%d"))
    target_day = int(IST_DAY)
    target_time = datetime.strptime(IST_TIME, "%H:%M").time()

    # Calculate time difference in minutes
    current_total_minutes = now.hour * 60 + now.minute
    target_total_minutes = target_time.hour * 60 + target_time.minute
    diff_minutes = abs(current_total_minutes - target_total_minutes)

    if current_day != target_day or diff_minutes > 5:
        print(f"[skip] Not in window. Now IST={now.strftime('%d %H:%M')} target={IST_DAY} {IST_TIME}")
        sys.exit(0)


def send_text():
    """Send the WhatsApp message through Whapi."""
    url = f"{API_BASE}/messages/text"
    headers = {
        "Authorization": f"Bearer {WHAPI_TOKEN}",
        "Content-Type": "application/json"
    }
    body_text = f"{MESSAGE} @{DISPLAY_NAME}"
    payload = {"to": GROUP_ID, "body": body_text, "mentions": [MENTION_WAID]}

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"[http] {r.status_code} {r.text}")

    if r.status_code != 200:
        fail("Whapi rejected the request. Check token, group ID, or message format.")

    try:
        resp = r.json()
    except Exception:
        fail("Non-JSON response from API.")

    return (((resp or {}).get("message")) or {}).get("id")


def get_status(msg_id: str):
    """Check the delivery status of the sent message."""
    if not msg_id:
        return

    url = f"{API_BASE}/messages/{msg_id}"
    headers = {"Authorization": f"Bearer {WHAPI_TOKEN}"}
    r = requests.get(url, headers=headers, timeout=15)

    if r.status_code != 200:
        print(f"[warn] Status check failed: {r.status_code} {r.text}")
        return

    try:
        data = r.json()
    except Exception:
        print("[warn] Could not parse status JSON")
        return

    status = data.get("status")
    print(f"[status] message_id={msg_id} status={status}")
    return status


def main():
    """Main entry point."""
    validate()
    ist_gate()  # Only proceed if inside the ±5-minute window
    msg_id = send_text()

    # Quick poll for delivery status
    for _ in range(6):
        st = get_status(msg_id)
        if st in ("sent", "delivered", "read"):
            break
        time.sleep(2)


if __name__ == "__main__":
    main()
