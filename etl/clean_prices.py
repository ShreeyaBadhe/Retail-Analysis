"""
etl/clean_ebay_data.py
Clean raw eBay shoe listings scraped from crawler and save to cleaned CSV.

Run:  python etl/clean_ebay_data.py
"""

import pandas as pd
import re
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_PATH = os.path.join(BASE_DIR, "data", "ebay_raw.csv")
CLEAN_PATH = os.path.join(BASE_DIR, "data", "ebay_cleaned.csv")

# Load raw data
df = pd.read_csv(RAW_PATH)

# ─── Helper Cleaning Functions ──────────────────────────────

def clean_price(text):
    """Extract first numeric value from price string."""
    if pd.isna(text): return None
    match = re.findall(r"\d+\.?\d*", text)
    return float(match[0]) if match else None

def clean_discount(text):
    """Extract percent number from discount text."""
    if pd.isna(text): return None
    match = re.search(r"\d+", str(text))
    return int(match.group(0)) if match else None

def extract_brand(title):
    """Use first word in title as brand."""
    if pd.isna(title): return None
    return title.strip().split()[0].lower()

def clean_rating(text):
    """Extract float from rating string (e.g., '4.5 out of 5')."""
    if pd.isna(text): return None
    match = re.search(r"\d+\.?\d*", text)
    return float(match.group(0)) if match else None

# ─── Apply Cleaning ─────────────────────────────────────────

df["price"]        = df["price_now"].apply(clean_price)
df["original_price"] = df["price_orig"].apply(clean_price)
df["discount_pct"] = df["discount_pct"].apply(clean_discount)
df["brand"]        = df["title"].apply(extract_brand)
df["rating_num"]   = df["rating"].apply(clean_rating)

# Drop rows with no title or price
# Drop rows with no title or price
df = df.dropna(subset=["title", "price"])

# Keep product_url if it exists
if "product_url" in df.columns:
    df["product_url"] = df["product_url"]

# Save cleaned file
df.to_csv(CLEAN_PATH, index=False)
print(f"✅ Cleaned data saved to {CLEAN_PATH} — {len(df)} rows")

