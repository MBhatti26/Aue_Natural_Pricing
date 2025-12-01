-- PostgreSQL Migration: Add date_key to stg_price_snapshot
-- Run this on your PostgreSQL database after updating price_history

-- Add date_key column to stg_price_snapshot
ALTER TABLE aue.stg_price_snapshot 
ADD COLUMN date_key INT;

-- Add foreign key to date_dim (if date_dim exists in PostgreSQL)
-- Uncomment if you've created date_dim in PostgreSQL
-- ALTER TABLE aue.stg_price_snapshot 
-- ADD CONSTRAINT fk_stg_snapshot_date 
-- FOREIGN KEY (date_key) REFERENCES aue.date_dim(date_key);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_stg_snapshot_date_key 
ON aue.stg_price_snapshot(date_key);

-- Populate date_key from date_collected (if data exists)
-- This function parses "YYYYMMDD_HHMMSS" format
UPDATE aue.stg_price_snapshot
SET date_key = CAST(
    SUBSTRING(date_collected::TEXT FROM 1 FOR 8) AS INTEGER
)
WHERE date_collected IS NOT NULL
  AND date_collected::TEXT ~ '^\d{8}_\d{6}$';

-- Verify the update
SELECT 
    COUNT(*) as total_records,
    COUNT(date_key) as records_with_date_key,
    COUNT(*) - COUNT(date_key) as records_missing_date_key
FROM aue.stg_price_snapshot;

-- Show sample
SELECT 
    date_collected,
    date_key,
    price,
    currency
FROM aue.stg_price_snapshot
LIMIT 10;
