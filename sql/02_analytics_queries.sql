-- FinGuard analytics queries (portfolio / Tableau reference)

-- Monthly churn rate (active base at start of month vs churned that month)
SELECT
    strftime('%Y-%m', churn_date) AS churn_month,
    COUNT(*) AS churned_customers
FROM customers
WHERE status = 'churned' AND churn_date IS NOT NULL
GROUP BY churn_month
ORDER BY churn_month;

-- Cohort retention: customers still active 30/60/90 days after signup
SELECT
    strftime('%Y-%m', signup_date) AS cohort_month,
    COUNT(*) AS cohort_size,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS still_active
FROM customers
GROUP BY cohort_month
ORDER BY cohort_month;

-- High-risk customers with MRR exposure
SELECT
    c.id,
    c.company_name,
    c.plan,
    c.mrr,
    r.risk_score,
    r.risk_tier,
    r.usage_drop_pct,
    r.open_tickets
FROM customers c
JOIN customer_risk_scores r ON c.id = r.customer_id
WHERE c.status = 'active' AND r.risk_tier = 'high'
ORDER BY r.risk_score DESC, c.mrr DESC;

-- Churn drivers: average risk signals for churned vs active customers
SELECT
    c.status,
    AVG(r.usage_drop_pct) AS avg_usage_drop,
    AVG(r.days_since_login) AS avg_days_since_login,
    AVG(r.open_tickets) AS avg_open_tickets,
    AVG(r.payment_failures) AS avg_payment_failures
FROM customers c
LEFT JOIN customer_risk_scores r ON c.id = r.customer_id
GROUP BY c.status;
