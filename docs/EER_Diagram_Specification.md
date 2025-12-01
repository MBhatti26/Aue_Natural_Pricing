# EER (Enhanced Entity-Relationship) Diagram Specification
## Auê Natural Data Warehouse Schema

**For drawing in draw.io**

---

## 📊 ENTITIES & ATTRIBUTES

### 1. **pricing_source** (Dimension Table)
**Primary Key:** `source_id` (VARCHAR(20))

**Attributes:**
- `source_id` (PK) - VARCHAR(20) - "SRC00000001"
- `source_name` - VARCHAR(100) - "Oxylabs Google Shopping"
- `region` - VARCHAR(10) - "GB"

**Shape:** Rectangle with double border (dimension table)
**Color:** Light blue

---

### 2. **brand** (Dimension Table)
**Primary Key:** `brand_id` (VARCHAR(20))

**Attributes:**
- `brand_id` (PK) - VARCHAR(20) - "BRDec140568"
- `brand_name` - VARCHAR(200) - "Little Soap Company"

**Shape:** Rectangle with double border
**Color:** Light green

---

### 3. **category** (Dimension Table)
**Primary Key:** `category_id` (VARCHAR(20))

**Attributes:**
- `category_id` (PK) - VARCHAR(20) - "CAT4f1e3d60"
- `category_name` - VARCHAR(100) - "Shampoo Bar"

**Shape:** Rectangle with double border
**Color:** Light yellow

---

### 4. **retailer** (Dimension Table)
**Primary Key:** `retailer_id` (VARCHAR(20))
**Foreign Key:** `source_id` → pricing_source

**Attributes:**
- `retailer_id` (PK) - VARCHAR(20) - "RET0ad38a55"
- `source_id` (FK) - VARCHAR(20)
- `retailer_name` - VARCHAR(200) - "Amazon.co.uk"

**Shape:** Rectangle with double border
**Color:** Light purple

---

### 5. **product** (Main Entity / Dimension Table)
**Primary Key:** `product_id` (VARCHAR(20))
**Foreign Keys:** `brand_id` → brand, `category_id` → category

**Attributes:**
- `product_id` (PK) - VARCHAR(20) - "PRD459b7e1a"
- `product_name` - VARCHAR(500) - "Little Soap Company Eco Warrior..."
- `brand_id` (FK) - VARCHAR(20)
- `category_id` (FK) - VARCHAR(20)
- `size_value` - DECIMAL(10,3) - nullable
- `size_unit` - VARCHAR(20) - "ml", "g", etc.

**Shape:** Rectangle with thick border
**Color:** Light orange

---

### 6. **date_dim** (Date Dimension Table)
**Primary Key:** `date_key` (INT)

**Attributes:**
- `date_key` (PK) - INT - Format: YYYYMMDD (e.g., 20251108)
- `full_date` - DATE - Actual date (2025-11-08)
- `year` - INT - 2025
- `quarter` - INT - 1, 2, 3, 4
- `month` - INT - 1-12
- `month_name` - VARCHAR(20) - "November"
- `month_abbr` - CHAR(3) - "Nov"
- `week_of_year` - INT - 1-52
- `day_of_month` - INT - 1-31
- `day_of_week` - INT - 1-7 (Monday = 1)
- `day_name` - VARCHAR(20) - "Friday"
- `day_abbr` - CHAR(3) - "Fri"
- `is_weekend` - BOOLEAN - TRUE/FALSE
- `year_month` - VARCHAR(7) - "2025-11"
- `year_quarter` - VARCHAR(7) - "2025-Q4"

**Shape:** Rectangle with double border (dimension table)
**Color:** Light cyan / aqua

**Note:** Critical for time-series analysis in Power BI. Supports date hierarchies, drill-down, and temporal comparisons.

---

### 7. **price_history** (Fact Table / Transactional)
**Primary Key:** `price_id` (VARCHAR(20))
**Foreign Keys:** `product_id` → product, `retailer_id` → retailer, `date_key` → date_dim

**Attributes:**
- `price_id` (PK) - VARCHAR(20) - "PRC00000001"
- `product_id` (FK) - VARCHAR(20)
- `retailer_id` (FK) - VARCHAR(20)
- `date_key` (FK) - INT - 20251108
- `price` - DECIMAL(10,2) - 4.15
- `discount` - DECIMAL(10,2) - nullable
- `currency` - CHAR(3) - "GBP"
- `date_collected` - VARCHAR(20) - "20251108_120316" (audit trail)
- `url` - TEXT - nullable
- `thumbnail` - TEXT - nullable (base64 image data)

**Shape:** Rectangle with thick border
**Color:** Light pink / salmon

---

### 8. **stg_price_snapshot** (PostgreSQL version - used by matching engine)
**Primary Key:** `snapshot_id` (implicit)
**Foreign Keys:** `product_id` → product, `retailer_id` → retailer

**Attributes:**
- `product_id` (FK)
- `retailer_id` (FK)
- `price` - DECIMAL
- `currency` - CHAR(3)
- `date_collected` - TIMESTAMP

**Note:** This is a staging/snapshot table used by the matching engine.
Similar to price_history but with different structure for real-time processing.

**Shape:** Rectangle with dashed border (staging table)
**Color:** Light gray

---

## 🔗 RELATIONSHIPS

### 1. **pricing_source → retailer**
- **Type:** One-to-Many (1:M)
- **Cardinality:** 1 pricing_source has MANY retailers
- **Foreign Key:** retailer.source_id → pricing_source.source_id
- **Line:** Solid line with crow's foot on retailer side
- **Label:** "sources from"

---

### 2. **brand → product**
- **Type:** One-to-Many (1:M)
- **Cardinality:** 1 brand has MANY products
- **Foreign Key:** product.brand_id → brand.brand_id
- **Participation:** Partial (product.brand_id can be NULL)
- **Line:** Dashed line with crow's foot on product side
- **Label:** "manufactures"

---

### 3. **category → product**
- **Type:** One-to-Many (1:M)
- **Cardinality:** 1 category contains MANY products
- **Foreign Key:** product.category_id → category.category_id
- **Participation:** Total (every product must have a category)
- **Line:** Solid line with crow's foot on product side
- **Label:** "categorizes"

---

### 4. **product → price_history**
- **Type:** One-to-Many (1:M)
- **Cardinality:** 1 product has MANY price_history records (time series)
- **Foreign Key:** price_history.product_id → product.product_id
- **Participation:** Total (every price record belongs to a product)
- **Line:** Solid line with crow's foot on price_history side
- **Label:** "has price snapshots"

---

### 5. **retailer → price_history**
- **Type:** One-to-Many (1:M)
- **Cardinality:** 1 retailer has MANY price_history records
- **Foreign Key:** price_history.retailer_id → retailer.retailer_id
- **Participation:** Total (every price record comes from a retailer)
- **Line:** Solid line with crow's foot on price_history side
- **Label:** "sells at"

---

### 6. **date_dim → price_history**
- **Type:** One-to-Many (1:M)
- **Cardinality:** 1 date has MANY price_history records
- **Foreign Key:** price_history.date_key → date_dim.date_key
- **Participation:** Total (every price record has a date)
- **Line:** Solid line with crow's foot on price_history side
- **Label:** "recorded on"

**Note:** This is the KEY relationship for time-series analysis. Enables date hierarchies and temporal drill-down in Power BI.

---

### 7. **product → stg_price_snapshot**
- **Type:** One-to-Many (1:M)
- **Cardinality:** 1 product has MANY snapshots
- **Foreign Key:** stg_price_snapshot.product_id → product.product_id
- **Line:** Dashed line with crow's foot on snapshot side
- **Label:** "tracked in"

---

### 8. **retailer → stg_price_snapshot**
- **Type:** One-to-Many (1:M)
- **Cardinality:** 1 retailer has MANY snapshots
- **Foreign Key:** stg_price_snapshot.retailer_id → retailer.retailer_id
- **Line:** Dashed line with crow's foot on snapshot side
- **Label:** "offers"

---

## 📐 LAYOUT SUGGESTION FOR DRAW.IO

```
                    ┌─────────────────┐
                    │ pricing_source  │
                    │   (Dimension)   │
                    └────────┬────────┘
                             │
                             │ 1:M
                             ▼
         ┌─────────────────────────────┐
         │                             │
         │          ┌─────────────────┐│
         │  ┌───────│    retailer     ││
         │  │       │   (Dimension)   ││
         │  │       └────────┬────────┘│
         │  │                │         │
         │  │                │ 1:M     │
         │  │                ▼         │
         │  │       ┌─────────────────┐│       ┌─────────────────┐
         │  │  ┌────│ price_history   ││───────│    date_dim     │
         │  │  │    │  (Fact Table)   ││  1:M  │   (Dimension)   │
         │  │  │    └────────┬────────┘│       │  **TIME KEY**   │
         │  │  │             │         │       └─────────────────┘
         │  │  │             │ M:1     │
         │  │  │             ▼         │
         │  │  │    ┌─────────────────┐│
         │  │  └────│    product      ││────┐
         │  │       │  (Main Entity)  ││    │
         │  │       └────────┬────────┘│    │
         │  │                │         │    │
         │  │           M:1  │  M:1    │    │
         │  │                ▼         ▼    │
         │  │       ┌─────────────┐  ┌─────────────┐
         │  │       │   category  │  │    brand    │
         │  │       │ (Dimension) │  │ (Dimension) │
         │  │       └─────────────┘  └─────────────┘
         │  │
         │  │ 1:M
         │  ▼
         │  ┌─────────────────┐
         └──│stg_price_snapshot│
            │   (Staging)      │
            └──────────────────┘
```

**Key Changes for Date Dimension:**
- **date_dim** connected to **price_history** with 1:M relationship
- This enables proper time-series analysis (year → quarter → month → day drill-down)
- Place date_dim prominently as it's critical for Power BI dashboards

---

## 🎨 DRAW.IO FORMATTING GUIDE

### Colors:
- **Dimension Tables** (blue): #D4E6F1 (pricing_source, brand, category, retailer)
- **Date Dimension** (cyan/aqua): #D5F4E6 (date_dim) - CRITICAL FOR POWER BI
- **Main Entity** (orange): #FCE5CD (product)
- **Fact Table** (pink/salmon): #F8CECC (price_history)
- **Staging Table** (gray): #E8E8E8 (stg_price_snapshot)

### Lines:
- **Solid line** = total participation / mandatory
- **Dashed line** = partial participation / optional
- **Crow's foot (>)** = "many" side of relationship
- **Single line (|)** = "one" side of relationship

### Text:
- **Bold** for entity names
- **Italic** for foreign keys (FK)
- **Underline** for primary keys (PK)

---

## 📊 DATA WAREHOUSE CHARACTERISTICS

### Star Schema Pattern:
- **Fact Table:** `price_history` (center)
- **Dimension Tables:** `date_dim` (TIME), `product`, `retailer`, `category`, `brand`, `pricing_source`
- **Measures:** price, discount
- **Time Dimension:** date_dim.date_key (enables drill-down: year → quarter → month → day)

### Key Features:
1. **Temporal tracking:** price_history stores time-series data
2. **Hierarchies:**
   - retailer → pricing_source
   - product → brand
   - product → category
3. **Degenerate dimensions:** price_id, product_id (surrogate keys)
4. **Slowly Changing Dimensions (SCD):**
   - Type 1: product (overwrite)
   - Type 2: price_history (append new records)

---

## 🔍 CARDINALITY SUMMARY

| Relationship | Cardinality | Participation |
|---|---|---|
| pricing_source → retailer | 1:M | Total |
| brand → product | 1:M | Partial (NULL allowed) |
| category → product | 1:M | Total |
| product → price_history | 1:M | Total |
| retailer → price_history | 1:M | Total |
| **date_dim → price_history** | **1:M** | **Total (CRITICAL)** |
| product → stg_price_snapshot | 1:M | Total |
| retailer → stg_price_snapshot | 1:M | Total |

---

## 📝 NOTES

1. **Date Dimension - CRITICAL UPDATE:**
   - **NEW:** Added `date_dim` table to support proper time-series analysis in Power BI
   - `price_history.date_key` → `date_dim.date_key` (foreign key relationship)
   - Original `date_collected` kept as VARCHAR for audit trail
   - **Benefits:**
     - Enables year → quarter → month → day drill-down
     - Supports weekend vs weekday analysis
     - Allows week-over-week, month-over-month comparisons
     - Pre-computed attributes improve query performance
   - **Implementation:** Run `sql/date_dimension_schema.sql` to add date_dim

2. **Matching Engine Integration:**
   - The matching engine queries `product`, `brand`, `category`, `retailer`, and `stg_price_snapshot`
   - SQL query joins all these tables to create a denormalized view for matching

3. **Data Flow:**
   ```
   Oxylabs API → raw CSV → cleaned CSV → database import → 
   product/brand/category/retailer/price_history → 
   date_dim (parse date_collected) → 
   stg_price_snapshot → matching engine → 
   processed_matches.csv / unmatched_products.csv
   ```

4. **PostgreSQL vs MySQL:**
   - PostgreSQL uses schema `aue` for namespacing
   - MySQL uses table prefixes and simpler structure
   - Both support the same logical model including date_dim

---

**Generated:** December 1, 2025  
**For:** Auê Natural Competitive Intelligence Pipeline  
**Database:** PostgreSQL (primary), MySQL (alternative)
