-- ============================================
-- Week 1: Business Queries - Retail BI Dashboard
-- ============================================

-- 1. Total sales by category: revenue, units, transaction count
SELECT
    p.category,
    SUM(s.total_amount) AS total_revenue,
    SUM(s.units_sold) AS total_units,
    COUNT(*) AS num_transactions
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;


-- 2. Monthly revenue trend: shows seasonality (Diwali/New Year spikes)
SELECT
    DATE_TRUNC('month', sale_date) AS month,
    SUM(total_amount) AS monthly_revenue,
    COUNT(*) AS num_transactions
FROM sales
GROUP BY DATE_TRUNC('month', sale_date)
ORDER BY month;


-- 3. Top 10 products by revenue
SELECT
    p.product_name,
    p.category,
    SUM(s.total_amount) AS total_revenue,
    SUM(s.units_sold) AS total_units
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.product_name, p.category
ORDER BY total_revenue DESC
LIMIT 10;


-- 4. Regional performance: revenue and transactions by state, normalized per store
SELECT
    st.region,
    SUM(s.total_amount) AS total_revenue,
    SUM(s.units_sold) AS total_units,
    COUNT(*) AS num_transactions,
    ROUND(SUM(s.total_amount) / COUNT(DISTINCT st.store_id), 2) AS avg_revenue_per_store
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY st.region
ORDER BY total_revenue DESC;