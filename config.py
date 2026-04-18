import os
from dotenv import load_dotenv

load_dotenv()


GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY", "")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY", "")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

YOUR_NAME = os.getenv("YOUR_NAME", "")
YOUR_COMPANY = os.getenv("YOUR_COMPANY", "Bunz Webby")
YOUR_PHONE = os.getenv("YOUR_PHONE", "")
YOUR_WEBSITE = os.getenv("YOUR_WEBSITE", "")

# ── Target Industries ──
# Only massive-money industries. Every one of these is the kind of company
# doing $5M-$500M+/year in revenue. These are the sectors where companies
# are too busy making money to care about their website.
TARGET_INDUSTRIES = [
    # Mining, quarrying, aggregates — $10M-$1B+ companies
    "mining corporation",
    "gold mining company",
    "coal mining corporation",
    "copper mining company",
    "quarry operator",
    "sand and gravel producer",
    "aggregate mining company",
    "mineral exploration company",
    "lithium mining company",
    "phosphate mining company",
    # Oil, gas, energy — $50M-$100B+ companies
    "oilfield services corporation",
    "oil drilling contractor",
    "pipeline construction company",
    "natural gas company",
    "offshore drilling company",
    "petroleum company",
    "refinery services company",
    "midstream oil and gas company",
    # Heavy civil / infrastructure — $10M-$1B+ companies
    "heavy civil construction company",
    "bridge construction company",
    "highway construction contractor",
    "dam construction company",
    "tunnel construction company",
    "marine construction contractor",
    "railroad construction company",
    # Commercial / industrial construction — $20M-$500M+ companies
    "commercial general contractor",
    "industrial construction company",
    "power plant construction contractor",
    "refinery construction contractor",
    "data center construction company",
    # Steel, metals, foundries — $10M-$500M+ companies
    "steel manufacturing company",
    "structural steel fabricator",
    "steel service center",
    "aluminum manufacturer",
    "iron foundry",
    "metal stamping company",
    "steel pipe manufacturer",
    "steel distributor",
    # Concrete, asphalt, materials — $10M-$200M+ companies
    "ready mix concrete company",
    "precast concrete manufacturer",
    "asphalt producer",
    "cement manufacturer",
    "building materials manufacturer",
    # Heavy equipment & fleet — $20M-$500M+ companies
    "heavy equipment rental company",
    "crane rental company",
    "earthmoving company",
    "fleet management company",
    # Trucking & freight — $10M-$1B+ companies
    "trucking corporation",
    "freight carrier company",
    "heavy haul transportation",
    "bulk carrier trucking",
    "tanker trucking company",
    "flatbed trucking company",
    # Waste, environmental, recycling — $10M-$500M+ companies
    "waste management corporation",
    "industrial waste services",
    "scrap metal recycling company",
    "hazardous waste disposal company",
    "demolition and environmental company",
    # Industrial manufacturing — $10M-$1B+ companies
    "industrial manufacturer",
    "chemical manufacturer",
    "plastics manufacturer",
    "paper mill company",
    "glass manufacturer",
    "lumber mill company",
    "packaging manufacturer",
    # Agriculture at scale — $10M-$500M+ companies
    "grain elevator corporation",
    "agricultural commodity company",
    "feed mill corporation",
    "fertilizer company",
    "seed company",
    "livestock company",
    # Utilities & infrastructure — $50M-$10B+ companies
    "electric utility company",
    "water utility company",
    "telecommunications infrastructure company",
    "fiber optic construction company",
]

# Website quality thresholds
WEBSITE_SCORE_THRESHOLD = 50  # Out of 100 — below this is "bad"

OUTPUT_DIR = "leads_output"
