# PGIMER Notice Watcher

Watches the "PGIMER Forthcoming Examinations" board on
https://pgimer.edu.in/PGIMER_PORTAL/PGIMERPORTAL/home.jsp and sends you a
Telegram message + email the moment a notice matching your keywords appears
(default: anything with "nursing" + "council"/"counsel"/"round 2" — tuned to
catch the B.Sc Nursing 4-year round-2 counselling notice, however PGIMER
phrases it).

Runs for free on GitHub Actions every 30 minutes, even if your PC is off.

## 1. Push this to a GitHub repo

```bash
cd pgi-notice-watcher
git init
git add .
git commit -m "PGIMER notice watcher"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

Repo can be private — Actions still work on private repos for free (within
GitHub's free minutes quota, which is generous for a job this small).

## 2. Set up Telegram alerts

1. Open Telegram, message **@BotFather**, send `/newbot`, follow the prompts.
   You'll get a **bot token** like `123456:ABC-DEF...`.
2. Message **@userinfobot** (or start a chat with your new bot and send it
   any message) to find your **chat ID** — a number like `987654321`.
3. Save both — you'll add them as GitHub secrets in step 4.

## 3. Set up email alerts (Gmail example)

1. Turn on 2-Step Verification on your Google account if not already on.
2. Go to https://myaccount.google.com/apppasswords and generate an **App
   Password** for "Mail". Copy the 16-character code.
3. You'll use your Gmail address + this app password (not your normal Gmail
   password) as secrets.

Using a different provider? Set `SMTP_HOST` / `SMTP_PORT` secrets to match
(defaults are Gmail's `smtp.gmail.com:465`).

## 4. Add GitHub repo secrets

In your repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add:

| Secret name           | Value                                  |
|------------------------|-----------------------------------------|
| `TELEGRAM_BOT_TOKEN`  | from BotFather                          |
| `TELEGRAM_CHAT_ID`    | your chat ID                            |
| `EMAIL_ADDRESS`       | your Gmail address                      |
| `EMAIL_APP_PASSWORD`  | the 16-char app password                |
| `EMAIL_TO`            | where you want the alert sent (can be same as EMAIL_ADDRESS) |

## 5. Enable and test

1. Go to the **Actions** tab in your repo → enable workflows if prompted.
2. Click **PGIMER Notice Watcher** → **Run workflow** to trigger it manually.
3. Check the run logs: it prints how many candidate rows it found on the
   page and whether anything matched. This tells you immediately whether the
   scraping is working, before you wait for a real notice to appear.

Once confirmed working, it'll run automatically every 30 minutes via the
cron schedule in `.github/workflows/check-notice.yml`.

## Tuning the keywords

Open `watch_notice.py` and edit near the top:

```python
REQUIRED_ALL = ["nursing"]
REQUIRED_ANY = ["council", "counsel", "round 2", "round-2", "2nd round", "ii round", "2nd counsel"]
```

A notice must contain **all** words in `REQUIRED_ALL` and **at least one**
phrase from `REQUIRED_ANY` to trigger an alert. If your first test run in
step 5 shows it's matching too broadly (e.g. picking up unrelated nursing
notices) or too narrowly (missing the one you want), tighten or loosen these
lists and re-run.

## Important note on reliability

The notice board on PGIMER's homepage loads its table dynamically (not
plain server-rendered HTML), so this script uses a headless browser
(Playwright) rather than a simple HTTP scraper — it reads whatever text is
actually rendered on the page, which is more robust to the exact markup than
targeting one specific CSS selector.

That said, I wasn't able to test this script against the live site from my
current environment (network access here is restricted to a small set of
dev domains and doesn't include pgimer.edu.in). **Please run it manually
once (step 5) before relying on it** — if the logs show 0 candidate rows
found, the site's markup may need a small tweak to the row-detection logic
in `fetch_notices()`. Send me the log output and I can adjust it.
