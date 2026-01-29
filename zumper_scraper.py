import time
import pandas as pd
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- CONFIGURATION ---
TARGET_CITIES = ['toronto-on', 'ottawa-on', 'mississauga-on', 'hamilton-on', 'london-on', 'kitchener-on']
MAX_LISTINGS = 60

def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def clean_price(price_text):
    if not price_text: return None
    clean = price_text.replace('$', '').replace(',', '').strip()
    if re.search(r'[\-\–]', clean):
        try:
            parts = re.split(r'[\-\–]', clean)
            return int((float(parts[0]) + float(parts[1])) / 2)
        except:
            return None
    try:
        return int(float(clean))
    except:
        return None

def parse_address_strict(url, city_slug):
    # 1. PROVINCE CHECK
    if "-on" not in url.lower(): return None 
    # 2. CITY CHECK
    target_city = city_slug.replace('-on', '')
    if target_city not in url.lower(): return None 

    try:
        slug = url.split('/')[-1]
        slug = re.sub(r'^p[0-9]+-', '', slug) 
        slug = re.sub(r'-p[0-9]+$', '', slug) 
        slug = slug.replace(f'-{target_city}-on', '')
        address = slug.replace('-', ' ').title().strip()
        
        if len(address) < 3 or "Bedroom" in address or "Apartment" in address:
            return None
        return address
    except:
        return None

def extract_beds_universal(card_soup):
    """
    Scans ALL text in the card to find bedroom info.
    Matches: 'Studio', '1 Bed', '2 Beds', '1-2 Beds', '3 Bd', '4 Bedrooms'
    """
    # 1. Get all text chunks from the card
    text_chunks = list(card_soup.stripped_strings)
    
    # 2. Regex to find Bed info
    # (?i) = case insensitive
    # Matches "Studio", or digits followed by "Bed/Bd/Bedroom"
    bed_pattern = re.compile(r'(?i)(\bStudio\b|\d+\s*(?:-|–)?\s*\d*\s*B(ed|d))')
    
    for text in text_chunks:
        # Skip Price (contains $)
        if '$' in text: continue
        
        # Check for Bed pattern
        match = bed_pattern.search(text)
        if match:
            return text.strip() # Return the full text (e.g., "Studio - 2 Beds")
            
    return "Unknown"

def scrape_city_v8(driver, city_slug):
    url = f"https://www.zumper.com/apartments-for-rent/{city_slug}"
    print(f"\n🌍 Navigating to: {city_slug.upper()}...")
    driver.get(url)
    time.sleep(5) 

    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    listings = []
    processed_links = set()
    
    cards = soup.find_all("div", recursive=True)
    
    for card in cards:
        if len(listings) >= MAX_LISTINGS: break
        
        try:
            # A. LINK CHECK
            link_tag = card.find("a", href=True)
            if not link_tag: continue
            href = link_tag['href']
            if "/apartments-for-rent/" not in href and "/apartment-buildings/" not in href: continue
            full_link = f"https://www.zumper.com{href}"
            if full_link in processed_links: continue

            # B. PRICE CHECK
            price_tag = card.find(string=re.compile(r'^\$[0-9]'))
            if not price_tag: continue
            final_price = clean_price(price_tag.strip())
            if not final_price: continue

            # C. ADDRESS CHECK
            address = parse_address_strict(full_link, city_slug)
            if not address: continue

            # D. UNIVERSAL BEDS CHECK (New Logic)
            bed_text = extract_beds_universal(card)
            
            # E. SAVE
            city_name = city_slug.replace('-on', '').title()
            full_address = f"{address}, {city_name}, ON, Canada"

            listings.append({
                "City": city_name,
                "Price": final_price,
                "Beds": bed_text,
                "Address": full_address,
                "Link": full_link
            })
            processed_links.add(full_link)
            
        except:
            continue

    return listings

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    driver = setup_driver()
    all_data = []
    
    try:
        for city in TARGET_CITIES:
            data = scrape_city_v8(driver, city)
            print(f"✅ Found {len(data)} listings in {city}")
            all_data.extend(data)
            time.sleep(2)
            
        if all_data:
            df = pd.DataFrame(all_data)
            df = df.drop_duplicates(subset=['Link'])
            
            # Filter out rows where Beds is still "Unknown" (Optional, but cleaner)
            # df = df[df['Beds'] != "Unknown"] 
            
            filename = "zumper_ontario_final.csv"
            df.to_csv(filename, index=False)
            print(f"\n💾 SUCCESS! Saved '{filename}'")
            print(df[['City', 'Price', 'Beds']].head(10))
        else:
            print("❌ No data found.")
            
    finally:
        driver.quit()