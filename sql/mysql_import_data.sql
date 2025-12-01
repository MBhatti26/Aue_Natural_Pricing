-- MySQL Data Import Script for Aue Natural Pricing Database
-- This script imports data from CSV files into the database tables
-- Run this script after creating the database schema with mysql_schema.sql

-- Ensure we're using the correct database
USE aue_natural_pricing;

-- Disable foreign key checks temporarily to avoid insertion order issues
SET FOREIGN_KEY_CHECKS = 0;

-- Import date_dim data (must be imported before price_history due to foreign key)
LOAD DATA LOCAL INFILE './database_to_import/date_dim.csv'
INTO TABLE date_dim
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(date_key, full_date, year, quarter, month, month_name, week, 
 day_of_month, day_of_week, day_name, is_weekend, year_month, year_quarter);

-- Import pricing_source data (this table has preset data, but can be extended)
-- Note: pricing_source is already populated by schema.sql, but you can add more sources here

-- Import brand_name data
LOAD DATA LOCAL INFILE './database_to_import/brand_name.csv'
INTO TABLE brand_name
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(brand_id, brand_name);

-- Import category_name data  
LOAD DATA LOCAL INFILE './database_to_import/category_name.csv'
INTO TABLE category_name
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(category_id, category_name);

-- Import retailer_name data
LOAD DATA LOCAL INFILE './database_to_import/retailer_name.csv'
INTO TABLE retailer_name
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(retailer_id, source_id, retailer_name);

-- Import product data
LOAD DATA LOCAL INFILE './database_to_import/product.csv'
INTO TABLE product
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(product_id, product_name, @brand_id, category_id, @size_value, @size_unit)
SET 
    brand_id = NULLIF(@brand_id, ''),
    size_value = NULLIF(@size_value, ''),
    size_unit = NULLIF(@size_unit, '');

-- Import price_history data (including url, thumbnail, and date_key columns)
LOAD DATA LOCAL INFILE './database_to_import/price_history.csv'
INTO TABLE price_history
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(price_id, product_id, retailer_id, price, @discount, currency, date_collected, @date_key, @url, @thumbnail)
SET 
    discount = NULLIF(@discount, ''),
    date_key = NULLIF(@date_key, ''),
    url = NULLIF(@url, ''),
    thumbnail = NULLIF(@thumbnail, '');

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- Display import summary
SELECT 'Data Import Complete' as Status;

-- Show record counts for verification
SELECT 
    'date_dim' as table_name, COUNT(*) as record_count FROM date_dim
UNION ALL
SELECT 
    'brand_name' as table_name, COUNT(*) as record_count FROM brand_name
UNION ALL
SELECT 
    'category_name' as table_name, COUNT(*) as record_count FROM category_name  
UNION ALL
SELECT 
    'pricing_source' as table_name, COUNT(*) as record_count FROM pricing_source
UNION ALL
SELECT 
    'retailer_name' as table_name, COUNT(*) as record_count FROM retailer_name
UNION ALL
SELECT 
    'product' as table_name, COUNT(*) as record_count FROM product
UNION ALL
SELECT 
    'price_history' as table_name, COUNT(*) as record_count FROM price_history;

-- Sample query to verify url and thumbnail data
SELECT 
    p.product_name,
    r.retailer_name,
    ph.price,
    ph.currency,
    ph.date_collected,
    CASE 
        WHEN ph.url IS NOT NULL THEN 'URL Present' 
        ELSE 'No URL' 
    END as url_status,
    CASE 
        WHEN ph.thumbnail IS NOT NULL THEN 'Thumbnail Present' 
        ELSE 'No Thumbnail' 
    END as thumbnail_status
FROM price_history ph
JOIN product p ON ph.product_id = p.product_id
JOIN retailer_name r ON ph.retailer_id = r.retailer_id
LIMIT 10;
