import pandas as pd
import requests
import time
import urllib3

# --- 1. DISABLE SSL WARNINGS ---
# This suppresses the big red warning messages you would otherwise see
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 2. LOAD DATA ---
input_file = "zumper_ontario_final.csv"
try:
    df = pd.read_csv(input_file)
    print(f"📍 Loaded {len(df)} listings from '{input_file}'")
except FileNotFoundError:
    print(f"❌ Critical Error: Could not find '{input_file}'. Make sure it is in the same folder!")
    exit()

# --- 3. THE GEOCODER FUNCTION ---
def geocode_arcgis_force(address):
    """
    Uses the ArcGIS API directly with SSL Verification DISABLED.
    """
    url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
    params = {
        "f": "json",
        "singleLine": address,
        "maxLocations": 1
    }
    
    try:
        # verify=False is the MAGIC KEY that fixes your Mac error
        response = requests.get(url, params=params, verify=False, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("candidates"):
                location = data["candidates"][0]["location"]
                return location["y"], location["x"] # Returns Lat, Lon
            
    except Exception as e:
        print(f"   Request error: {e}")
        
    return None, None

# --- 4. RUN LOOP ---
print("🚀 Starting Geocoding (Bypassing SSL checks)...")
lats = []
lons = []

for index, row in df.iterrows():
    address = row['Address']
    lat, lon = geocode_arcgis_force(address)
    
    if lat:
        print(f"✅ [{index+1}/{len(df)}] {address[:30]}... -> {lat:.4f}, {lon:.4f}")
        lats.append(lat)
        lons.append(lon)
    else:
        print(f"⚠️ [{index+1}/{len(df)}] Not Found: {address}")
        lats.append(None)
        lons.append(None)
        
    # Be polite to the server
    time.sleep(0.2)

# --- 5. SAVE ---
df['Latitude'] = lats
df['Longitude'] = lons

# Keep only the rows we successfully mapped
df_clean = df.dropna(subset=['Latitude', 'Longitude'])

output_file = "zumper_geocoded_final.csv"
df_clean.to_csv(output_file, index=False)

print(f"\n💾 DONE! Saved '{output_file}' with {len(df_clean)} locations.")
