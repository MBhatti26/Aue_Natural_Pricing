-- Date Dimension Table for Time-Series Analysis
-- Adds proper date dimension to support Power BI analytics

-- =====================================================
-- CREATE DATE DIMENSION TABLE
-- =====================================================

CREATE TABLE date_dim (
    date_key INT PRIMARY KEY,                    -- Format: YYYYMMDD (e.g., 20251108)
    full_date DATE NOT NULL,                     -- Actual date
    year INT NOT NULL,                           -- 2025
    quarter INT NOT NULL,                        -- 1, 2, 3, 4
    month INT NOT NULL,                          -- 1-12
    month_name VARCHAR(20) NOT NULL,             -- January, February, etc.
    month_abbr CHAR(3) NOT NULL,                 -- Jan, Feb, etc.
    week_of_year INT NOT NULL,                   -- 1-52
    day_of_month INT NOT NULL,                   -- 1-31
    day_of_week INT NOT NULL,                    -- 1-7 (Monday = 1)
    day_name VARCHAR(20) NOT NULL,               -- Monday, Tuesday, etc.
    day_abbr CHAR(3) NOT NULL,                   -- Mon, Tue, etc.
    is_weekend BOOLEAN NOT NULL,                 -- TRUE/FALSE
    is_holiday BOOLEAN DEFAULT FALSE,            -- TRUE/FALSE
    fiscal_year INT,                             -- For fiscal year analysis
    fiscal_quarter INT,                          -- Fiscal quarter
    year_month VARCHAR(7) NOT NULL,              -- Format: 2025-01
    year_quarter VARCHAR(7) NOT NULL,            -- Format: 2025-Q1
    CONSTRAINT UQ_date_dim_date UNIQUE (full_date)
);

-- Create indexes for common queries
CREATE INDEX idx_date_dim_year_month ON date_dim(year, month);
CREATE INDEX idx_date_dim_full_date ON date_dim(full_date);
CREATE INDEX idx_date_dim_quarter ON date_dim(year, quarter);


-- =====================================================
-- ALTER EXISTING TABLES TO ADD DATE_KEY
-- =====================================================

-- Add date_key to price_history (fact table)
ALTER TABLE price_history 
ADD COLUMN date_key INT,
ADD CONSTRAINT fk_price_history_date 
    FOREIGN KEY (date_key) REFERENCES date_dim(date_key);

-- Create index on date_key for fast joins
CREATE INDEX idx_price_history_date_key ON price_history(date_key);


-- =====================================================
-- FUNCTION TO PARSE DATE FROM date_collected STRING
-- =====================================================

DELIMITER //

CREATE FUNCTION parse_date_key(date_string VARCHAR(20))
RETURNS INT
DETERMINISTIC
BEGIN
    -- Input format: "20251108_120316"
    -- Output: 20251108 (YYYYMMDD as integer)
    RETURN CAST(LEFT(date_string, 8) AS UNSIGNED);
END//

CREATE FUNCTION parse_full_date(date_string VARCHAR(20))
RETURNS DATE
DETERMINISTIC
BEGIN
    -- Input format: "20251108_120316"
    -- Output: DATE '2025-11-08'
    DECLARE year_part VARCHAR(4);
    DECLARE month_part VARCHAR(2);
    DECLARE day_part VARCHAR(2);
    
    SET year_part = SUBSTRING(date_string, 1, 4);
    SET month_part = SUBSTRING(date_string, 5, 2);
    SET day_part = SUBSTRING(date_string, 7, 2);
    
    RETURN STR_TO_DATE(CONCAT(year_part, '-', month_part, '-', day_part), '%Y-%m-%d');
END//

DELIMITER ;


-- =====================================================
-- POPULATE DATE DIMENSION
-- =====================================================

-- Generate dates from 2024-01-01 to 2026-12-31 (adjust range as needed)
DELIMITER //

CREATE PROCEDURE populate_date_dim()
BEGIN
    DECLARE current_date DATE;
    DECLARE end_date DATE;
    DECLARE date_key_val INT;
    
    SET current_date = '2024-01-01';
    SET end_date = '2026-12-31';
    
    WHILE current_date <= end_date DO
        SET date_key_val = CAST(DATE_FORMAT(current_date, '%Y%m%d') AS UNSIGNED);
        
        INSERT INTO date_dim (
            date_key,
            full_date,
            year,
            quarter,
            month,
            month_name,
            month_abbr,
            week_of_year,
            day_of_month,
            day_of_week,
            day_name,
            day_abbr,
            is_weekend,
            year_month,
            year_quarter
        ) VALUES (
            date_key_val,
            current_date,
            YEAR(current_date),
            QUARTER(current_date),
            MONTH(current_date),
            DATE_FORMAT(current_date, '%M'),
            DATE_FORMAT(current_date, '%b'),
            WEEK(current_date, 1),
            DAY(current_date),
            DAYOFWEEK(current_date),
            DATE_FORMAT(current_date, '%W'),
            DATE_FORMAT(current_date, '%a'),
            CASE WHEN DAYOFWEEK(current_date) IN (1, 7) THEN TRUE ELSE FALSE END,
            DATE_FORMAT(current_date, '%Y-%m'),
            CONCAT(YEAR(current_date), '-Q', QUARTER(current_date))
        );
        
        SET current_date = DATE_ADD(current_date, INTERVAL 1 DAY);
    END WHILE;
END//

DELIMITER ;

-- Execute the population procedure
CALL populate_date_dim();


-- =====================================================
-- UPDATE EXISTING price_history RECORDS
-- =====================================================

-- Update date_key for all existing price_history records
UPDATE price_history
SET date_key = parse_date_key(date_collected)
WHERE date_key IS NULL;


-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Check date dimension population
SELECT 
    COUNT(*) as total_dates,
    MIN(full_date) as earliest_date,
    MAX(full_date) as latest_date,
    COUNT(DISTINCT year) as years_covered
FROM date_dim;

-- Check price_history date_key population
SELECT 
    COUNT(*) as total_records,
    COUNT(date_key) as records_with_date_key,
    COUNT(*) - COUNT(date_key) as records_missing_date_key
FROM price_history;

-- Sample join between price_history and date_dim
SELECT 
    d.full_date,
    d.day_name,
    d.month_name,
    d.year,
    COUNT(ph.price_id) as price_records
FROM date_dim d
LEFT JOIN price_history ph ON d.date_key = ph.date_key
WHERE d.full_date >= '2025-11-01'
GROUP BY d.full_date, d.day_name, d.month_name, d.year
ORDER BY d.full_date
LIMIT 20;


-- =====================================================
-- POWER BI RECOMMENDED QUERIES
-- =====================================================

-- Query 1: Price trends over time with proper date hierarchy
SELECT 
    d.year,
    d.quarter,
    d.month,
    d.month_name,
    d.full_date,
    d.day_name,
    COUNT(DISTINCT ph.product_id) as unique_products,
    COUNT(ph.price_id) as total_price_points,
    AVG(ph.price) as avg_price,
    MIN(ph.price) as min_price,
    MAX(ph.price) as max_price
FROM date_dim d
INNER JOIN price_history ph ON d.date_key = ph.date_key
GROUP BY d.year, d.quarter, d.month, d.month_name, d.full_date, d.day_name
ORDER BY d.full_date;

-- Query 2: Week-over-week price changes
SELECT 
    d.year,
    d.week_of_year,
    COUNT(DISTINCT ph.product_id) as products_tracked,
    AVG(ph.price) as avg_price
FROM date_dim d
INNER JOIN price_history ph ON d.date_key = ph.date_key
GROUP BY d.year, d.week_of_year
ORDER BY d.year, d.week_of_year;

-- Query 3: Weekend vs weekday pricing
SELECT 
    d.is_weekend,
    CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END as day_type,
    COUNT(ph.price_id) as price_observations,
    AVG(ph.price) as avg_price
FROM date_dim d
INNER JOIN price_history ph ON d.date_key = ph.date_key
GROUP BY d.is_weekend
ORDER BY d.is_weekend;


-- =====================================================
-- NOTES
-- =====================================================

/*
1. Date Dimension Benefits:
   - Enables proper time-series analysis in Power BI
   - Supports drill-down (year → quarter → month → day)
   - Allows weekend/weekday analysis
   - Facilitates fiscal year reporting
   - Optimizes query performance with pre-computed attributes

2. Integration with Existing Schema:
   - price_history.date_key → date_dim.date_key
   - Original date_collected field kept for audit trail
   - Parse functions extract date_key from date_collected format

3. Power BI Usage:
   - Create date hierarchy: Year > Quarter > Month > Day
   - Use full_date for date slicers
   - Use year_month for month-over-month analysis
   - Use is_weekend for comparative analysis

4. Maintenance:
   - Run populate_date_dim() when extending date range
   - Update date_key when importing new price_history records
   - Consider adding is_holiday flags for major holidays
*/
