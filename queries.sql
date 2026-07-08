--Total sales by category: revenue, units, transaction count
SELECT
    p.category,
    SUM(s.total_amount) AS total_revenue,
    SUM(s.units_sold) AS total_units,
    COUNT(*) AS num_transactions
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;

-- Monthly revenue trend: shows seasonality (Diwali/New Year spikes)
SELECT
    DATE_TRUNC('month', sale_date) AS month,
    SUM(total_amount) AS monthly_revenue,
    COUNT(*) AS num_transactions
FROM sales
GROUP BY DATE_TRUNC('month', sale_date)
ORDER BY month;