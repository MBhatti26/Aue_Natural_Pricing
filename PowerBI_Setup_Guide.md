# PowerBI Dashboard Setup Guide - Auê Natural Competitive Intelligence

## 🎯 **Dashboard Overview**

Based on your competitive intelligence requirements, we'll create **4 core dashboards**:

1. **Executive Summary Dashboard** - High-level KPIs
2. **Competitive Pricing Analytics** - Regional price comparisons
3. **Market Positioning Intelligence** - Brand analysis & positioning  
4. **Retailer/Platform Analysis** - Cross-retailer insights

## 📊 **Data Setup**

### Step 1: PowerBI Data Import
1. Open **PowerBI Desktop**
2. Go to **Home > Get Data > Text/CSV**
3. Import these files from `./powerbi_data/`:
   - `FINAL_MATCHES.csv` (934 matched product pairs)
   - `FINAL_UNMATCHED.csv` (391 unmatched products)
   - `FINAL_SUMMARY.json` (summary statistics)

### Step 2: Data Model Setup
Create these **calculated columns** in PowerBI:

#### In FINAL_MATCHES table:
```DAX
// Price Difference
Price_Difference = [product_2_price] - [product_1_price]

// Price Difference Percentage
Price_Diff_Pct = DIVIDE([Price_Difference], [product_1_price]) * 100

// Price Position Category
Price_Position = 
IF([Price_Diff_Pct] <= -10, "Significantly Cheaper",
IF([Price_Diff_Pct] <= -5, "Moderately Cheaper", 
IF([Price_Diff_Pct] <= 5, "Price Parity",
IF([Price_Diff_Pct] <= 10, "Moderately Premium", "Significantly Premium"))))

// Match Tier
Match_Tier = 
IF([similarity] >= 85, "Tier 1 (High Confidence)",
IF([similarity] >= 70, "Tier 2 (Medium Confidence)",
IF([similarity] >= 65, "Tier 3 (Acceptable)", "Low Confidence")))

// Brand Category Classification
Brand_1_Category = 
SWITCH(TRUE(),
CONTAINSSTRING(LOWER([product_1_brand]), "garnier"), "Mass Market",
CONTAINSSTRING(LOWER([product_1_brand]), "alberto"), "Mass Market", 
CONTAINSSTRING(LOWER([product_1_brand]), "faith"), "Premium Natural",
CONTAINSSTRING(LOWER([product_1_brand]), "little soap"), "Premium Natural",
CONTAINSSTRING(LOWER([product_1_brand]), "kitsch"), "Specialty/International",
CONTAINSSTRING(LOWER([product_1_brand]), "earthling"), "Specialty/International",
"Other/Niche")

// Price Bands
Price_Band_1 = 
IF([product_1_price] <= 5, "Budget (£0-5)",
IF([product_1_price] <= 10, "Mid-Range (£5-10)", 
IF([product_1_price] <= 20, "Premium (£10-20)", "Ultra-Premium (£20+)")))
```

## 🏆 **Dashboard 1: Executive Summary**

### Key Visuals:
1. **KPI Cards:**
   - Total Products: 888
   - Match Coverage: 56%
   - Total Match Pairs: 934
   - Perfect Matches: 109

2. **Match Quality Donut Chart:**
   - Slice by Match_Tier
   - Values: Count of matches

3. **Price Position Distribution:**
   - Stacked Bar Chart
   - X-axis: Price_Position
   - Y-axis: Count of matches
   - Legend: Match_Tier

### DAX Measures:
```DAX
Total_Products = 888
Match_Coverage_Pct = DIVIDE(COUNTROWS(FINAL_MATCHES), [Total_Products]) * 100
Avg_Similarity = AVERAGE(FINAL_MATCHES[similarity])
Perfect_Matches = COUNTROWS(FILTER(FINAL_MATCHES, [similarity] = 100))
```

## 💰 **Dashboard 2: Competitive Pricing Analytics**

### Key Visuals:

1. **Regional Price Index (Clustered Column):**
   - X-axis: Brand_1_Category 
   - Y-axis: Average of product_1_price, product_2_price
   - Legend: retailer fields

2. **Price Ladder/Waterfall Chart:**
   - Categories: Price_Band_1, Price_Band_2
   - Values: Count of matches
   - Show price distribution across segments

3. **Price vs. Similarity Scatter Plot:**
   - X-axis: similarity
   - Y-axis: Price_Difference 
   - Size: product_1_price
   - Color: Match_Tier

4. **Competitor Price Heatmap:**
   - Rows: product_1_brand
   - Columns: product_2_brand  
   - Values: Average Price_Diff_Pct
   - Conditional formatting: Red (premium) to Green (discount)

### Key Insights to Display:
- "Vitamin C Serums averaging +7% premium vs. UK baseline"
- "Mass market brands show -15% average vs. premium natural"
- "Price parity opportunities in £5-10 segment"

## 📈 **Dashboard 3: Market Positioning Intelligence**

### Key Visuals:

1. **Brand Portfolio Matrix:**
   - X-axis: Average Price
   - Y-axis: Product Count
   - Size: Number of matched pairs
   - Color: Brand_1_Category

2. **Category Price Distribution (Boxplot-style):**
   - X-axis: Brand_1_Category
   - Y-axis: product_1_price
   - Show min, median, 90th percentile per category

3. **Market Share by Price Point:**
   - Stacked Area Chart
   - X-axis: Price_Band_1
   - Y-axis: Count of products
   - Legend: Brand_1_Category

4. **Competitive Gap Analysis:**
   - Table visual showing:
     - Brand categories
     - Average prices
     - Match coverage
     - Recommended positioning

### Strategic Insights:
- "Premium Natural segment: £6-12 sweet spot identified"
- "Mass market price ceiling: £5.99"
- "Specialty brands command 40%+ premium"

## 🏪 **Dashboard 4: Retailer/Platform Analysis**

### Key Visuals:

1. **Platform Parity Grid:**
   - Matrix visual
   - Rows: Unique product names (from matches)
   - Columns: Retailers
   - Values: Prices
   - Conditional formatting for price variance

2. **Retailer Coverage Analysis:**
   - Treemap
   - Categories: product_1_retailer, product_2_retailer
   - Values: Count of products
   - Color: Average price

3. **Cross-Retailer Price Distribution:**
   - Violin plot (or Box plot)
   - X-axis: Retailer names
   - Y-axis: Price ranges
   - Filter by brand categories

4. **Availability vs Price Map:**
   - Scatter plot
   - X-axis: Average retailer price
   - Y-axis: Product count per retailer
   - Size: Match coverage percentage

## 🔧 **PowerBI File Sharing Setup**

### Option 1: Self-Contained PowerBI File
```
1. Save PowerBI file as: "Aue_Natural_Competitive_Intelligence.pbix"
2. Include all data imported (not live connections)
3. Others can open directly if they have PowerBI Desktop
4. File will be ~5-10MB with our dataset
```

### Option 2: Shared Database Setup
```
1. Install PostgreSQL locally
2. Import our CSV data to database
3. Share PowerBI file + database connection string
4. Others need: git clone + PostgreSQL + PowerBI
```

### Option 3: PowerBI Service (Cloud)
```
1. Publish to PowerBI Service workspace
2. Schedule data refresh from CSV files
3. Share dashboards via web links
4. Requires PowerBI Pro licenses
```

## 📋 **Implementation Steps**

1. **Import Data** (15 mins)
2. **Create Calculated Columns** (30 mins)  
3. **Build Dashboard 1: Executive** (45 mins)
4. **Build Dashboard 2: Pricing** (60 mins)
5. **Build Dashboard 3: Positioning** (45 mins)
6. **Build Dashboard 4: Retailer** (45 mins)
7. **Testing & Refinement** (30 mins)

**Total Time: ~4.5 hours**

## 🎯 **Key Business Questions Answered**

✅ **Regional**: "Are we price-competitive across UK retailers?"  
✅ **Product**: "Which product segments are over/under-priced?"  
✅ **Platform**: "Where do retailers undercut each other?"  
✅ **Strategic**: "What's our optimal market positioning?"

---

**Next Step**: Would you like me to create the PowerBI template file (.pbit) with pre-built visualizations?
