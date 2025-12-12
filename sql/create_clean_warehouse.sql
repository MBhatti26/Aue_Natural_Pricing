-- ============================================================================
-- AUÊ NATURAL - WAREHOUSE SCHEMA
-- Matches EER_DIAGRAM_SPEC.md EXACTLY
-- Direct mapping from CSV outputs - NO transformations
-- ============================================================================

DROP SCHEMA IF EXISTS aue CASCADE;
CREATE SCHEMA aue;

-- ============================================================================
-- TABLE 1: MATCHED_PRODUCTS
-- Source: data/processed/processed_matches.csv
-- ============================================================================

CREATE TABLE aue.matched_products (
    -- Primary Key
    match_id BIGSERIAL PRIMARY KEY,
    
    -- Product 1 (Auê Natural Product)
    product_1_id TEXT,
    product_1_name TEXT,
    brand_1 TEXT,
    size_value_1 NUMERIC,
    size_unit_1 TEXT,
    price_1 NUMERIC(12,2),
    currency_1 TEXT,
    date_collected_1 TIMESTAMP,
    date_key_1 INTEGER,
    retailer_1 TEXT,
    
    -- Product 2 (Matched Retailer Product)
    product_2_id TEXT,
    product_2_name TEXT,
    brand_2 TEXT,
    size_value_2 NUMERIC,
    size_unit_2 TEXT,
    price_2 NUMERIC(12,2),
    currency_2 TEXT,
    date_collected_2 TIMESTAMP,
    date_key_2 INTEGER,
    retailer_2 TEXT,
    
    -- Common Attributes
    category TEXT,
    
    -- Similarity Scores (Match Quality Analysis)
    similarity NUMERIC(5,2),
    hybrid_name_similarity NUMERIC(5,2),
    lexical_similarity NUMERIC(5,2),
    semantic_similarity NUMERIC(5,2),
    brand_similarity NUMERIC(5,2),
    size_similarity NUMERIC(5,2),
    
    -- Metadata
    import_ts TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_matched_product_1_id ON aue.matched_products(product_1_id);
CREATE INDEX idx_matched_product_2_id ON aue.matched_products(product_2_id);
CREATE INDEX idx_matched_category ON aue.matched_products(category);
CREATE INDEX idx_matched_date_1 ON aue.matched_products(date_key_1);
CREATE INDEX idx_matched_date_2 ON aue.matched_products(date_key_2);
CREATE INDEX idx_matched_similarity ON aue.matched_products(similarity);

COMMENT ON TABLE aue.matched_products IS 'Products successfully matched between Auê Natural catalog and retailer listings';

-- ============================================================================
-- TABLE 2: UNMATCHED_PRODUCTS
-- Source: data/processed/unmatched_products.csv
-- ============================================================================

CREATE TABLE aue.unmatched_products (
    -- Primary Key
    unmatched_id BIGSERIAL PRIMARY KEY,
    
    -- Product Identification
    product_id TEXT,
    product_name TEXT,
    brand_id TEXT,
    brand_name TEXT,
    category_id TEXT,
    category_name TEXT,
    
    -- Product Attributes
    size_value NUMERIC,
    size_unit TEXT,
    price NUMERIC(12,2),
    currency TEXT,
    date_collected TIMESTAMP,
    date_key INTEGER,
    retailer_name TEXT,
    
    -- Cleaned/Normalized Fields
    product_clean TEXT,
    brand_clean TEXT,
    category_clean TEXT,
    retailer_clean TEXT,
    size_value_norm NUMERIC,
    size_unit_norm TEXT,
    
    -- Match Metadata
    incomplete_record BOOLEAN,
    reason_unmatched TEXT,
    
    -- Metadata
    import_ts TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_unmatched_product_id ON aue.unmatched_products(product_id);
CREATE INDEX idx_unmatched_category ON aue.unmatched_products(category_name);
CREATE INDEX idx_unmatched_brand ON aue.unmatched_products(brand_name);
CREATE INDEX idx_unmatched_date ON aue.unmatched_products(date_key);
CREATE INDEX idx_unmatched_retailer ON aue.unmatched_products(retailer_name);

COMMENT ON TABLE aue.unmatched_products IS 'Products that could not be matched (for manual review or reprocessing)';

-- ============================================================================
-- ANALYTICS VIEWS
-- ============================================================================

-- View 1: All Products (Union of matched and unmatched)
CREATE VIEW aue.all_products AS
SELECT 
    'matched' AS record_type,
    product_1_id AS product_id,
    product_1_name AS product_name,
    brand_1 AS brand,
    category,
    size_value_1 AS size_value,
    size_unit_1 AS size_unit,
    price_1 AS price,
    currency_1 AS currency,
    date_key_1 AS date_key,
    retailer_1 AS retailer,
    similarity,
    import_ts
FROM aue.matched_products
UNION ALL
SELECT 
    'unmatched' AS record_type,
    product_id,
    product_name,
    brand_name AS brand,
    category_name AS category,
    size_value,
    size_unit,
    price,
    currency,
    date_key,
    retailer_name AS retailer,
    NULL AS similarity,
    import_ts
FROM aue.unmatched_products;

COMMENT ON VIEW aue.all_products IS 'Union of matched and unmatched products for complete catalog analysis';

-- View 2: Price Comparison
CREATE VIEW aue.price_comparison AS
SELECT 
    product_1_name,
    brand_1,
    category,
    retailer_1,
    price_1,
    retailer_2,
    price_2,
    (price_2 - price_1) AS price_diff,
    ROUND(((price_2 - price_1) / NULLIF(price_1, 0) * 100)::NUMERIC, 2) AS price_diff_pct,
    similarity,
    date_key_1
FROM aue.matched_products
WHERE price_1 IS NOT NULL AND price_2 IS NOT NULL
ORDER BY ABS((price_2 - price_1) / NULLIF(price_1, 0) * 100) DESC;

COMMENT ON VIEW aue.price_comparison IS 'Price differences between matched products';

-- View 3: Best Matches by Category
CREATE VIEW aue.best_matches_by_category AS
SELECT 
    category,
    COUNT(*) AS match_count,
    ROUND(AVG(similarity), 2) AS avg_similarity,
    ROUND(MIN(similarity), 2) AS min_similarity,
    ROUND(MAX(similarity), 2) AS max_similarity
FROM aue.matched_products
GROUP BY category
ORDER BY match_count DESC;

COMMENT ON VIEW aue.best_matches_by_category IS 'Match quality statistics grouped by category';

-- View 4: Retailer Coverage
CREATE VIEW aue.retailer_coverage AS
SELECT 
    retailer_name,
    COUNT(*) AS product_count,
    COUNT(DISTINCT category) AS category_count,
    ROUND(AVG(price), 2) AS avg_price
FROM (
    SELECT retailer_1 AS retailer_name, category, price_1 AS price FROM aue.matched_products
    UNION ALL
    SELECT retailer_2 AS retailer_name, category, price_2 AS price FROM aue.matched_products
) AS combined
WHERE price IS NOT NULL
GROUP BY retailer_name
ORDER BY product_count DESC;

COMMENT ON VIEW aue.retailer_coverage IS 'Retailer product catalog size and pricing';

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

GRANT USAGE ON SCHEMA aue TO mahnoorbhatti;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA aue TO mahnoorbhatti;
GRANT SELECT ON ALL TABLES IN SCHEMA aue TO mahnoorbhatti;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA aue TO mahnoorbhatti;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 'Schema created successfully!' AS status;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'aue' ORDER BY table_name;
