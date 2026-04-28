# Bunz Webby Lead Scraper

Finds massive, high-revenue companies (mining, steel, construction, oil & gas, manufacturing, etc.) with bad websites, plus well-reviewed local companies that have no website listed on Google. It previews outreach by default and only sends live emails when you pass `--send`.

## What It Does

1. **Discovers website leads** — Searches Google across high-revenue industry categories to find companies with websites worth analyzing
2. **Discovers no-website leads** — Uses Google Places to find companies with strong ratings/review counts and no website link listed
3. **Analyzes websites** — Scores each company's website on SSL, mobile-friendliness, speed, modern code, and SEO
4. **Finds emails** — Uses Hunter.io, website scraping, and public search results for no-website leads
5. **Sends carefully** — Live sends are capped per day, spaced out with randomized delays, and tracked to avoid repeats

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API keys
```bash
cp .env.example .env
```

Edit `.env` and add your keys:

| Key | Required | Where to get it |
|-----|----------|----------------|
| `GOOGLE_SEARCH_API_KEY` | **Yes** (or use free scraping fallback) | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — Enable "Custom Search API" |
| `GOOGLE_SEARCH_CX` | **Yes** (with API key) | [Programmable Search Engine](https://programmablesearchengine.google.com/) — Create one, set to search the whole web |
| `GOOGLE_PLACES_API_KEY` | Recommended | Same Google Cloud key, with Places API enabled. Used for rated businesses with no website listed |
| `SMTP_EMAIL` / `SMTP_USERNAME` / `SMTP_PASSWORD` | **Yes** (to send) | SendGrid: `SMTP_USERNAME=apikey`, `SMTP_EMAIL` is your verified sender, and `SMTP_PASSWORD` is your SendGrid API key |
| `HUNTER_API_KEY` | Optional | [Hunter.io](https://hunter.io/api) — 25 free searches/month |
| `PAGESPEED_API_KEY` | Optional | Same Google Cloud Console — works without key too |

**Note:** If you don't set `GOOGLE_SEARCH_API_KEY`, the scraper falls back to direct Google scraping (no API needed, but may get rate-limited).

### 3. Fill in your business info in `.env`
```
YOUR_NAME=John Smith
YOUR_COMPANY=Bunz Webby
YOUR_PHONE=713-555-0100
YOUR_WEBSITE=https://bunzwebby.com
PAST_PROJECT_NAME=Gulf States Materials
PAST_PROJECT_URL=https://gulfstatesmaterials.com
PAST_PROJECT_DISPLAY_URL=gulfstatesmaterials.com
```

For SendGrid SMTP, set:

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_EMAIL=you@yourverifieddomain.com
SMTP_PASSWORD=your_sendgrid_api_key_here
DISABLE_SENDGRID_CLICK_TRACKING=true
```

### 4. Set your sending pace
The defaults are intentionally conservative:

```env
MAX_EMAILS_PER_DAY=25
EMAIL_DELAY_MIN_SECONDS=600
EMAIL_DELAY_MAX_SECONDS=2700
SKIP_PREVIOUSLY_EMAILED=true
USE_GUESSED_EMAILS=false
```

Successful live sends are recorded in `leads_output/email_send_history.csv`, so the 10/day cap and duplicate protection work across multiple runs.

### 5. Set no-website targeting
```env
ENABLE_NO_WEBSITE_PLACES=true
TARGET_LOCATIONS=Houston TX
MIN_GOOGLE_RATING=4.2
MIN_GOOGLE_REVIEW_COUNT=25
PLACES_RESULTS_PER_QUERY=8
```

Use comma-separated locations for broader searches, for example `TARGET_LOCATIONS=Houston TX,Dallas TX,Austin TX`.

### 6. Scheduled background outreach
The scheduled worker is designed for Windows Task Scheduler. It wakes up, checks whether it is a configured business day and business hour, sends a small batch if there is daily capacity, writes logs, sends the end-of-day report, then exits.

The Windows tasks created for this workspace are:
- `BunzWebbyScheduledOutreach` — runs weekdays at 9:00 AM, then every 30 minutes for 8 hours
- `BunzWebbyScheduledOutreachReport` — runs weekdays at 5:05 PM to send the daily report

On macOS, use the included `launchd` installer instead of Windows Task Scheduler:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your real API keys and sender settings
chmod +x run_scheduled_outreach.sh run_scheduled_report.sh setup_macos_launchd.sh uninstall_macos_launchd.sh
./setup_macos_launchd.sh
```

The macOS launch agents are:
- `com.bunzwebby.scheduled-outreach` — runs weekdays from 9:00 AM through 4:30 PM every 30 minutes
- `com.bunzwebby.scheduled-outreach-report` — runs weekdays at 5:05 PM to send the daily report

Useful macOS checks:

```bash
launchctl list | grep bunzwebby
python scheduled_outreach.py status
tail -f leads_output/scheduled_outreach_task.log
```

To remove the macOS jobs:

```bash
./uninstall_macos_launchd.sh
```

```env
SCHEDULED_OUTREACH_ENABLED=true
SCHEDULED_DAILY_EMAIL_LIMIT=25
SCHEDULED_MAX_EMAILS_PER_RUN=2
SCHEDULED_INTRA_RUN_DELAY_SECONDS=30
SCHEDULED_TASK_INTERVAL_MINUTES=30
BUSINESS_DAYS=MON,TUE,WED,THU,FRI
BUSINESS_HOURS_START=09:00
BUSINESS_HOURS_END=17:00
SCHEDULED_AUTO_REFILL_QUEUE=true
SCHEDULED_REFILL_MIN_QUEUE=10
SCHEDULED_REFILL_LIMIT=50
REPORT_RECIPIENTS=lucas@iqventoryllc.com,amoreno@iqventoryllc.com
```

Useful commands:

```bash
python scheduled_outreach.py status
python scheduled_outreach.py refill --force
python scheduled_outreach.py run --dry-run
python scheduled_outreach.py report --dry-run --force
```

Generated scheduler files go to `leads_output/`:
- `scheduled_outreach_queue.json` — queued leads waiting to be sent
- `scheduled_outreach_activity.csv` — sent/failed/skipped scheduled outreach rows
- `scheduled_report_history.csv` — daily report send history
- `scheduled_outreach_task.log` — Windows Task Scheduler run log

## Usage

### Dry run (preview everything, send nothing)
```bash
python main.py
```

### Actually send, capped at 10/day by default
```bash
python main.py --send
```

### Search only rated businesses with no website listed
```bash
python main.py --places-only --location "Houston TX"
```

### Target specific industries
```bash
python main.py --industry "gold mining company" --industry "steel fabrication"
```

### Skip PageSpeed analysis (faster runs)
```bash
python main.py --skip-pagespeed
```

### Override the send pace for a live run
```bash
python main.py --send --daily-limit 10 --min-delay 900 --max-delay 3600
```

## How It Chooses Leads

The scraper searches high-revenue industry categories including:
- **Mining & Extraction** — quarries, sand/gravel, coal, gold, minerals
- **Oil & Gas** — oilfield services, drilling, pipeline contractors
- **Heavy Construction** — commercial GCs, civil contractors, demolition, excavation, paving
- **Steel & Metals** — fabrication, structural steel, scrap metal, iron works
- **Materials & Distribution** — building materials, lumber, roofing, industrial supply
- **Manufacturing** — industrial manufacturers, machine shops, welders, custom fabrication
- **Trucking & Logistics** — freight, heavy haul
- **Agriculture** — grain elevators, feed mills, farm equipment
- **Waste & Environmental** — waste management, recycling, environmental services

For Google Places no-website leads, it keeps businesses that meet your configured minimum rating and review count, then confirms the place details do not include a website link.

Qualified leads are prioritized before sending. No-website leads get the strongest boost, then lower website scores, higher Google ratings, and larger review counts push leads higher in the send order.

## Output

All output goes to `leads_output/`:
- `leads_TIMESTAMP.csv` — All companies found with scores and emails
- `leads_TIMESTAMP.json` — Full detailed data
- `email_log_TIMESTAMP.csv` — Record of all emails sent
- `email_send_history.csv` — Persistent history used for daily caps and duplicate-send prevention
- `scheduled_outreach_activity.csv` — Scheduled outreach report source data

## How Website Scoring Works

Each website is scored 0-100:

| Score | Grade | Meaning |
|-------|-------|---------|
| 80+ | A | Good website, skip |
| 65-79 | B | Decent, probably skip |
| 50-64 | C | Mediocre, borderline lead |
| 35-49 | D | Bad website — hot lead |
| 0-34 | F | Terrible or no website — hottest lead |

Factors: SSL, mobile viewport tag, responsive CSS, outdated HTML tags, copyright year, PageSpeed performance, page builder detection.

## Project Structure

```
├── main.py               # Pipeline orchestrator & CLI
├── scraper.py            # Google Search-based big company discovery
├── website_analyzer.py   # Website quality scoring
├── email_finder.py       # Owner email discovery
├── emailer.py            # Email templates & SMTP sender
├── config.py             # Configuration, industries & env vars
├── requirements.txt
├── .env.example
└── leads_output/         # Generated CSV/JSON output
```