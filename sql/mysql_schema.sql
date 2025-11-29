-- MySQL Schema for Aue Natural Pricing Database
-- Converted from SQL Server schema for better compatibility

-- Create database (uncomment if needed)
-- CREATE DATABASE aue_natural_pricing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE aue_natural_pricing;

-- Create pricing_source table (equivalent to price_source.csv)
CREATE TABLE pricing_source (
    source_id VARCHAR(20) PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    region VARCHAR(10) NOT NULL
);

-- Create brand_name table
CREATE TABLE brand_name (
    brand_id VARCHAR(20) PRIMARY KEY,
    brand_name VARCHAR(200) NOT NULL
);

-- Create category_name table  
CREATE TABLE category_name (
    category_id VARCHAR(20) PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);

-- Create retailer_name table
CREATE TABLE retailer_name (
    retailer_id VARCHAR(20) PRIMARY KEY,
    source_id VARCHAR(20) NOT NULL,
    retailer_name VARCHAR(200) NOT NULL,
    FOREIGN KEY (source_id) REFERENCES pricing_source(source_id)
);

-- Create product table
CREATE TABLE product (
    product_id VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(500) NOT NULL,
    brand_id VARCHAR(20) NULL,
    category_id VARCHAR(20) NOT NULL,
    size_value DECIMAL(10,3) NULL,
    size_unit VARCHAR(20) NULL,
    FOREIGN KEY (brand_id) REFERENCES brand_name(brand_id),
    FOREIGN KEY (category_id) REFERENCES category_name(category_id)
);

-- Create price_history table
CREATE TABLE price_history (
    price_id VARCHAR(20) PRIMARY KEY,
    product_id VARCHAR(20) NOT NULL,
    retailer_id VARCHAR(20) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    discount DECIMAL(10,2) NULL,
    currency CHAR(3) NOT NULL DEFAULT 'GBP',
    date_collected VARCHAR(20) NOT NULL,
    url TEXT NULL,
    thumbnail TEXT NULL,
    FOREIGN KEY (product_id) REFERENCES product(product_id),
    FOREIGN KEY (retailer_id) REFERENCES retailer_name(retailer_id)
);

-- Create indexes for better performance
CREATE INDEX idx_product_brand ON product(brand_id);
CREATE INDEX idx_product_category ON product(category_id);
CREATE INDEX idx_price_history_product ON price_history(product_id);
CREATE INDEX idx_price_history_retailer ON price_history(retailer_id);
CREATE INDEX idx_price_history_date ON price_history(date_collected);

-- Insert initial pricing source data
INSERT INTO pricing_source (source_id, source_name, region) VALUES 
('SRC00000001', 'Oxylabs Google Shopping', 'GB');

-- Display table information
SHOW TABLES;

-- Table statistics (uncomment after data import)
/*
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
*/
