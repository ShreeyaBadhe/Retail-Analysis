# dashboard/app.py code remains same
# crawler/ebay_spider.py (updated)
"""
crawler/ebay_spider.py
Scrape eBay shoe listings across N pages and save to CSV
Run:  python crawler/ebay_spider.py
"""

import time, re, sys, traceback
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

NUM_PAGES    = 20
HEADLESS     = True
SCROLL_LOOPS = 15
SCROLL_WAIT  = 1.2
OUTPUT_PATH  = "data/ebay_raw.csv"
BASE_URL     = "https://www.ebay.com/sch/i.html?_nkw=shoes&_pgn={}"


def make_driver(headless=True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
    opts.add_argument("start-maximized")
    opts.add_argument("--no-sandbox")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36")
    return webdriver.Chrome(options=opts)


def smart_scroll(driver, loops:int, wait:float):
    prev=0
    for _ in range(loops):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(wait)
        curr=len(driver.find_elements(By.CSS_SELECTOR, "li.s-item"))
        if curr==prev:
            break
        prev=curr


def safe_text(el, css):
    elem=el.find_elements(By.CSS_SELECTOR, css)
    return elem[0].text.strip() if elem else ""


def scrape_page(driver):
    items=[]
    for card in driver.find_elements(By.CSS_SELECTOR, "li.s-item"):
        try:
            title=safe_text(card, ".s-item__title")
            if not title or "Shop on eBay" in title:
                continue
            # image
            try:
                image_url=card.find_element(By.CSS_SELECTOR, ".s-item__image-wrapper img").get_attribute("src")
            except:
                image_url=None
            # product link
            try:
                product_url=card.find_element(By.CSS_SELECTOR, "a.s-item__link").get_attribute("href")
            except:
                product_url=None

            items.append({
                "title":title,
                "price_now":safe_text(card, ".s-item__price"),
                "price_orig":safe_text(card, ".s-item__original-price"),
                "discount_pct":safe_text(card, ".s-item__discount"),
                "shipping":safe_text(card, ".s-item__shipping, .s-item__logisticsCost"),
                "rating":safe_text(card, ".b-starrating .clipped"),
                "image_url":image_url,
                "product_url":product_url
            })
        except Exception:
            traceback.print_exc(file=sys.stderr)
            continue
    return items


def main():
    driver=make_driver(HEADLESS)
    all_items=[]
    try:
        for p in range(1,NUM_PAGES+1):
            driver.get(BASE_URL.format(p))
            time.sleep(4)
            smart_scroll(driver,SCROLL_LOOPS,2.0)
            page_items=scrape_page(driver)
            all_items.extend(page_items)
            print(f"✅ Page {p}: {len(page_items)} items (total {len(all_items)})")
            time.sleep(1)
    finally:
        driver.quit()

    df=pd.DataFrame(all_items).drop_duplicates(subset=["title","price_now"])
    df.to_csv(OUTPUT_PATH,index=False)
    print(f"\n🎉 Done! Saved {len(df)} unique rows → {OUTPUT_PATH}")
    # simple check
    print(df["product_url"].notna().sum(),"links captured")

if __name__=="__main__":
    main()
