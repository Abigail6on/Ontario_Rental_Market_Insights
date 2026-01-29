import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# ==========================================
# 1. LOAD & PREPARE DATA
# ==========================================
print("🔄 Loading datasets...")

# Load your two final files
df_zumper = pd.read_csv("zumper_geocoded_final.csv")
df_amenity = pd.read_csv("features_amenity_density.csv")

# --- Function to clean "Beds" (e.g., "Studio-2 beds" -> 1.0) ---
def parse_beds(bed_str):
    if pd.isna(bed_str) or str(bed_str).lower() == 'unknown':
        return np.nan
    
    text = str(bed_str).lower()
    
    # Handle "Studio" (Treat as 0.5 beds to separate it from 1-bed)
    if 'studio' in text:
        # Check for range "Studio - 2 beds"
        nums = re.findall(r'\d+', text)
        if nums:
            # Average of 0 (Studio) and High
            return (0 + int(nums[0])) / 2
        return 0.5 
    
    # Handle standard ranges "1-3 beds"
    nums = re.findall(r'\d+', text)
    if len(nums) == 2:
        return (int(nums[0]) + int(nums[1])) / 2 # Average
    elif len(nums) == 1:
        return float(nums[0])
    
    return np.nan

# Apply bed cleaning
df_zumper['Beds_Num'] = df_zumper['Beds'].apply(parse_beds)
# Drop the few rows where beds are still unknown
df_zumper = df_zumper.dropna(subset=['Beds_Num'])

print(f"✅ Listings ready for modeling: {len(df_zumper)}")

# ==========================================
# 2. MERGE DATASETS
# ==========================================
# Normalize names to Title Case to ensure they match (e.g. "toronto" == "Toronto")
df_zumper['City_Clean'] = df_zumper['City'].str.strip().str.title()
df_amenity['City_Name_Clean'] = df_amenity['City_Name'].str.strip().str.title()

# Merge: Attach Amenity Scores to each Apartment
df_final = pd.merge(
    df_zumper, 
    df_amenity, 
    left_on='City_Clean', 
    right_on='City_Name_Clean', 
    how='left'
)

# Check if any rows failed to match
missing = df_final['Amenity_Count'].isnull().sum()
if missing > 0:
    print(f"⚠️ Warning: {missing} listings missing amenity data. Filling with median.")
    df_final['Amenity_Count'] = df_final['Amenity_Count'].fillna(df_final['Amenity_Count'].median())
else:
    print("✅ Merge Perfect: All listings have amenity data.")

# Save the master dataset for your records
df_final.to_csv("final_model_dataset.csv", index=False)
print("💾 Saved 'final_model_dataset.csv'")

# ==========================================
# 3. TRAIN THE AI MODEL
# ==========================================
print("\n🤖 Training Random Forest Model...")

# The features we use to predict Price
features = ['Beds_Num', 'Amenity_Count', 'Latitude', 'Longitude']
target = 'Price'

X = df_final[features]
y = df_final[target]

# Split: 80% for training, 20% for testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the Model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# ==========================================
# 4. RESULTS & INSIGHTS
# ==========================================
predictions = model.predict(X_test)

# Calculate Accuracy Metrics
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("-" * 40)
print(f"📊 MODEL PERFORMANCE REPORT")
print("-" * 40)
print(f"Average Error (MAE): ${mae:.2f}")
print(f"Accuracy Score (R²): {r2:.2f} (Target: > 0.50)")

print("\n🌟 WHAT DRIVES RENT PRICES IN ONTARIO?")
importances = model.feature_importances_
feature_names = features
# Sort them
indices = np.argsort(importances)[::-1]
for i in range(len(features)):
    print(f"{i+1}. {feature_names[indices[i]]}: {importances[indices[i]]*100:.1f}%")

# ==========================================
# 5. VISUALIZATION
# ==========================================
plt.figure(figsize=(10, 6))
sns.scatterplot(x=y_test, y=predictions, alpha=0.7, color='blue')
# Draw a red line for perfect predictions
plt.plot([y.min(), y.max()], [y.min(), y.max()], 'r--', lw=2)
plt.xlabel("Actual Rent ($)")
plt.ylabel("Predicted Rent ($)")
plt.title(f"Prediction Accuracy (R² = {r2:.2f})")
plt.grid(True, linestyle='--', alpha=0.5)
plt.show()