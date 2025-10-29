USE MyFirstDatabase;
GO

-- Check retailer counts
SELECT 
    r.provider,
    r.domain,
    r.country_code,
    COUNT(DISTINCT p.product_id) as product_count,
    COUNT(ps.snapshot_id) as snapshot_count
FROM pricing.retailers r
LEFT JOIN pricing.products p ON r.retailer_id = p.retailer_id
LEFT JOIN pricing.price_snapshots ps ON p.product_id = ps.product_id
GROUP BY r.provider, r.domain, r.country_code
ORDER BY r.domain;

-- Check total counts
SELECT 
    (SELECT COUNT(*) FROM pricing.retailers) as total_retailers,
    (SELECT COUNT(*) FROM pricing.products) as total_products,
    (SELECT COUNT(*) FROM pricing.price_snapshots) as total_snapshots;

-- Sample data
SELECT TOP 10 * FROM pricing.products;
SELECT TOP 10 * FROM pricing.price_snapshots;