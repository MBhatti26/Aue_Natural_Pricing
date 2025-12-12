-- Query products by number of retailers offering them
SELECT product_id, COUNT(retailer_id) as retailer_count 
FROM aue.fact_price_snapshot 
GROUP BY product_id 
ORDER BY COUNT(retailer_id) DESC 
LIMIT 20;
