
USE MyFirstDatabase;
GO

-- Create the pricing schema
CREATE SCHEMA pricing AUTHORIZATION dbo;
GO

-- Create retailers table
CREATE TABLE pricing.retailers (
  retailer_id  INT IDENTITY PRIMARY KEY,
  provider     NVARCHAR(50) NOT NULL,
  domain       NVARCHAR(50) NOT NULL,
  country_code CHAR(2)      NULL,
  currency     CHAR(3)      NULL,
  CONSTRAINT UQ_retailers UNIQUE (provider, domain)
);

-- Create products table
CREATE TABLE pricing.products (
  product_id   BIGINT IDENTITY PRIMARY KEY,
  retailer_id  INT NOT NULL FOREIGN KEY REFERENCES pricing.retailers(retailer_id),
  external_id  NVARCHAR(100) NOT NULL,
  brand        NVARCHAR(200) NULL,
  title        NVARCHAR(500) NOT NULL,
  url          NVARCHAR(1000) NULL,
  CONSTRAINT UQ_products UNIQUE (retailer_id, external_id)
);
CREATE INDEX IX_products_brand ON pricing.products(brand);

-- Create price_snapshots table
CREATE TABLE pricing.price_snapshots (
  snapshot_id      BIGINT IDENTITY PRIMARY KEY,
  product_id       BIGINT NOT NULL FOREIGN KEY REFERENCES pricing.products(product_id),
  collected_at_utc DATETIME2 NOT NULL,
  currency         CHAR(3)   NOT NULL,
  current_price    DECIMAL(18,4) NOT NULL,
  list_price       DECIMAL(18,4) NULL,
  coupon_value     DECIMAL(18,4) NULL,
  coupon_type      NVARCHAR(40)  NULL,
  best_seller      BIT           NULL,
  is_prime         BIT           NULL,
  is_sponsored     BIT           NULL,
  availability     NVARCHAR(50)  NULL,
  shipping_info    NVARCHAR(200) NULL,
  rating           DECIMAL(6,3)  NULL,
  reviews_total    INT           NULL,
  sales_volume     INT           NULL,
  pos              INT           NULL,
  size_value       DECIMAL(18,6) NULL,
  size_unit        NVARCHAR(20)  NULL,
  price_per_100    DECIMAL(18,4) NULL,
  search_keyword   NVARCHAR(200) NULL,
  market_domain    NVARCHAR(50)  NULL
);
CREATE INDEX IX_snapshots_product_time ON pricing.price_snapshots(product_id, collected_at_utc DESC);
GO

-- Insert retailer data
INSERT INTO pricing.retailers(provider, domain, country_code, currency) VALUES
('oxylabs','co.uk','GB','GBP'),
('oxylabs','de','DE','EUR'),
('oxylabs','fr','FR','EUR'),
('oxylabs','it','IT','EUR'),
('oxylabs','es','ES','EUR'),
('oxylabs','nl','NL','EUR');
GO
USE MyFirstDatabase;
GO

SELECT TABLE_SCHEMA, TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'pricing';
USE MyFirstDatabase;
GO

SELECT COUNT(*) as product_count FROM pricing.products;
SELECT TOP 10 * FROM pricing.products;
USE MyFirstDatabase;
GO

SELECT COUNT(*) FROM pricing.products;
SELECT TOP 10 
    p.product_id,
    r.domain,
    p.external_id as ASIN,
    p.brand,
    p.title
FROM pricing.products p
JOIN pricing.retailers r ON p.retailer_id = r.retailer_id;
USE MyFirstDatabase;
GO

DECLARE @count INT;
SELECT @count = COUNT(*) FROM pricing.products;
PRINT 'Total products: ' + CAST(@count AS VARCHAR);

SELECT TOP 3
    CONCAT('Product: ', external_id, ' | Brand: ', ISNULL(brand, 'N/A'), ' | Title: ', LEFT(title, 50)) as ProductInfo
FROM pricing.products;