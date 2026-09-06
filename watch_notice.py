"""
PGIMER Notice Watcher
----------------------
Watches the PGIMER "Forthcoming Examinations" notice board on the homepage
for a notice matching your keywords (default: B.Sc Nursing round-2 counselling)
and sends a Telegram + Email alert the first time it appears.

Uses Playwright (headless Chromium) because the notice table on
pgimer.edu.in is loaded dynamically via JS, not plain server HTML.
"""

import os
import re
import json
import smtplib
import hashlib
from email.mime.text import MIMEText
from pathlib import Path

from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# CONFIG — edit this section to change what you're watching for
# ---------------------------------------------------------------------------

PGIMER_URL = "https://pgimer.edu.in/PGIMER_PORTAL/PGIMERPORTAL/home.jsp"

# A notice must contain ALL of these (case-insensitive) to be considered a candidate
REQUIRED_ALL = ["nursing"]

# ...and AT LEAST ONE of these (catches counselling/counseling, round 2, 2nd, etc.)
REQUIRED_ANY = ["council", "counsel", "round 2", "round-2", "2nd round", "ii round", "2nd counsel"]

STATE_FILE = Path(__file__).parent / "state" / "seen.json"

# ---------------------------------------------------------------------------
# SCRAPE
# ---------------------------------------------------------------------------

ROW_EXTRACT_JS = """
() => {
    const dateRegex = /[A-Za-z]{3}\\/\\d{1,2}\\/\\d{4}|\\d{1,2}[\\/\\-]\\d{1,2}[\\/\\-]\\d{2,4}/;
    const results = [];
    const all = document.querySelectorAll('tr, li, div');
    all.forEach(el => {
        const text = el.innerText ? el.innerText.trim() : '';
        if (!text || text.length > 400) return;
        if (dateRegex.test(text) && text.length > 15) {
            results.push(text.replace(/\\s+/g, ' '));
        }
    });
    return results;
}
"""


def fetch_notices():
    """
    Returns a list of notice row strings.
    The notice board on pgimer.edu.in's homepage is rendered inside an
    <iframe>, not the top-level document — so this checks the main page
    AND every frame on it, not just document.querySelectorAll on the top
    page (which cannot see into iframes even when same-origin).
    """
    notices = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(PGIMER_URL, wait_until="networkidle", timeout=60000)

        # Give any lazy AJAX widgets (including iframe contents) time to populate
        page.wait_for_timeout(5000)

        frames = page.frames
        print(f"Page loaded. Found {len(frames)} frame(s) total (including main frame).")

        rows = []
        for frame in frames:
            try:
                frame_rows = frame.evaluate(ROW_EXTRACT_JS)
                if frame_rows:
                    print(f"  Frame '{frame.url}' contributed {len(frame_rows)} row(s).")
                rows.extend(frame_rows)
            except Exception as e:
                # Cross-origin frames (e.g. ad/analytics widgets) can't be
                # evaluated — that's fine, skip them.
                print(f"  Skipped frame '{frame.url}' ({e.__class__.__name__}).")

        browser.close()

    # De-duplicate while preserving order
    seen_lines = set()
    for r in rows:
        if r not in seen_lines:
            seen_lines.add(r)
            notices.append(r)

    return notices


def matches_keywords(text: str) -> bool:
    t = text.lower()
    if not all(k in t for k in REQUIRED_ALL):
        return False
    return any(k in t for k in REQUIRED_ANY)


# ---------------------------------------------------------------------------
# STATE (so we only alert once per notice)
# ---------------------------------------------------------------------------

def load_seen():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_seen(seen_set):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(seen_set), indent=2))


def notice_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


# ---------------------------------------------------------------------------
# ALERTS
# ---------------------------------------------------------------------------

def send_telegram(message: str):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("Telegram not configured, skipping.")
        return
    import urllib.request
    import urllib.parse

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
    req = urllib.request.Request(url, data=data)
    try:
        urllib.request.urlopen(req, timeout=15)
        print("Telegram alert sent.")
    except Exception as e:
        print(f"Telegram send failed: {e}")


def send_email(subject: str, body: str):
    email_addr = os.environ.get("EMAIL_ADDRESS")
    email_pass = os.environ.get("EMAIL_APP_PASSWORD")
    to_addr = os.environ.get("EMAIL_TO", email_addr)
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))

    if not email_addr or not email_pass:
        print("Email not configured, skipping.")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = email_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(email_addr, email_pass)
            server.sendmail(email_addr, [to_addr], msg.as_string())
        print("Email alert sent.")
    except Exception as e:
        print(f"Email send failed: {e}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("Fetching PGIMER notice board...")
    notices = fetch_notices()
    print(f"Found {len(notices)} candidate rows on the page.")

    seen = load_seen()
    new_matches = []

    for text in notices:
        if matches_keywords(text):
            h = notice_hash(text)
            if h not in seen:
                new_matches.append(text)
                seen.add(h)

    if new_matches:
        print(f"New matching notice(s) found: {len(new_matches)}")
        body_lines = [
            "New PGIMER notice matching your watch (B.Sc Nursing / counselling):",
            "",
        ]
        for m in new_matches:
            body_lines.append(f"- {m}")
        body_lines.append("")
        body_lines.append(f"Check: {PGIMER_URL}")
        body = "\n".join(body_lines)

        send_telegram(body)
        send_email("PGIMER Notice Alert: B.Sc Nursing counselling", body)

        save_seen(seen)
    else:
        print("No new matching notices this run.")


if __name__ == "__main__":
    main()
