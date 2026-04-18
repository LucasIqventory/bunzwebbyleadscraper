# Bunz Webby Lead Scraper

Finds massive, high-revenue companies (mining, steel, construction, oil & gas, manufacturing, etc.) with bad or missing websites — then emails their owners with a pitch to rebuild their site.

## What It Does

1. **Discovers big companies** — Searches Google across 50+ high-revenue industry categories (mining, steel, oil & gas, heavy construction, trucking, manufacturing, etc.) to find companies pulling $1M+/year
2. **Scores "bigness"** — Ranks leads by revenue signals: employee count, years in business, multiple locations, dollar amounts mentioned, corporate structure (Inc, Corp, Holdings)
3. **Analyzes websites** — Scores each company's website on SSL, mobile-friendliness, speed, modern code, and SEO
4. **Finds owner emails** — Uses Hunter.io, website scraping, and pattern matching to find decision-maker emails
5. **Sends outreach** — Personalized cold emails based on whether they have no website or a bad one

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
| `SMTP_EMAIL` / `SMTP_PASSWORD` | **Yes** (to send) | Gmail: use [App Passwords](https://myaccount.google.com/apppasswords) |
| `HUNTER_API_KEY` | Optional | [Hunter.io](https://hunter.io/api) — 25 free searches/month |
| `PAGESPEED_API_KEY` | Optional | Same Google Cloud Console — works without key too |

**Note:** If you don't set `GOOGLE_SEARCH_API_KEY`, the scraper falls back to direct Google scraping (no API needed, but may get rate-limited).

### 3. Fill in your business info in `.env`
```
YOUR_NAME=John Smith
YOUR_COMPANY=Bunz Webby
YOUR_PHONE=713-555-0100
YOUR_WEBSITE=https://bunzwebby.com
```

## Usage

### Dry run (preview everything, send nothing)
```bash
python main.py
```

### Target specific industries
```bash
python main.py --industry "gold mining company" --industry "steel fabrication"
```

### Only keep leads that look like big companies
```bash
python main.py --min-bigness 3
```

### Skip PageSpeed analysis (faster runs)
```bash
python main.py --skip-pagespeed
```

### Actually send emails
```bash
python main.py --send --delay 60
```

## How It Finds Big Companies

The scraper searches 50+ industry categories including:
- **Mining & Extraction** — quarries, sand/gravel, coal, gold, minerals
- **Oil & Gas** — oilfield services, drilling, pipeline contractors
- **Heavy Construction** — commercial GCs, civil contractors, demolition, excavation, paving
- **Steel & Metals** — fabrication, structural steel, scrap metal, iron works
- **Materials & Distribution** — building materials, lumber, roofing, industrial supply
- **Manufacturing** — industrial manufacturers, machine shops, welders, custom fabrication
- **Trucking & Logistics** — freight, heavy haul
- **Agriculture** — grain elevators, feed mills, farm equipment
- **Waste & Environmental** — waste management, recycling, environmental services

Each company gets a **bigness score** based on signals like:
- Revenue/dollar amounts mentioned ("$50 million", "$2B revenue")
- Employee counts ("500 employees")
- Age ("established 1985", "since 1972")
- Scale ("12 locations", "nationwide fleet")
- Corporate structure (Inc, Corp, Holdings, Group)

## Output

All output goes to `leads_output/`:
- `leads_TIMESTAMP.csv` — All companies found with scores and emails
- `leads_TIMESTAMP.json` — Full detailed data
- `email_log_TIMESTAMP.csv` — Record of all emails sent

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