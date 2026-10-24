-- All-record reporting population: January-February 2025 archive.
-- No narrative-text filter is applied to these business metrics.

-- 1. Monthly product volume and change, using a window function.
WITH monthly AS (
    SELECT substr(date_received,1,7) AS month,product,COUNT(*) AS complaints
    FROM complaints GROUP BY 1,2
), previous AS (
    SELECT *,LAG(complaints) OVER(PARTITION BY product ORDER BY month) AS prior_month
    FROM monthly
)
SELECT *,ROUND(100.0*(complaints-prior_month)/NULLIF(prior_month,0),2) AS change_pct
FROM previous ORDER BY product,month;

-- 2. Top three reported issues in each product category.
WITH counts AS (
    SELECT product,issue,COUNT(*) AS complaints FROM complaints GROUP BY 1,2
), ranked AS (
    SELECT *,DENSE_RANK() OVER(PARTITION BY product ORDER BY complaints DESC) AS issue_rank
    FROM counts
)
SELECT * FROM ranked WHERE issue_rank<=3 ORDER BY product,issue_rank;

-- 3. Narrative coverage. The modeling subset differs from all-record analytics.
SELECT product,COUNT(*) AS complaints,SUM(has_narrative) AS narratives,
       ROUND(100.0*SUM(has_narrative)/COUNT(*),2) AS narrative_coverage_pct
FROM complaints GROUP BY product ORDER BY complaints DESC;

-- 4. Timely-response percentage with an explicit known-value denominator.
-- This is a source-provided binary flag, not a measured response duration.
SELECT product,
       SUM(CASE WHEN timely_response='Yes' THEN 1 ELSE 0 END) AS timely,
       SUM(CASE WHEN timely_response IN ('Yes','No') THEN 1 ELSE 0 END) AS known,
       ROUND(100.0*SUM(CASE WHEN timely_response='Yes' THEN 1 ELSE 0 END)/
             NULLIF(SUM(CASE WHEN timely_response IN ('Yes','No') THEN 1 ELSE 0 END),0),2) AS timely_pct
FROM complaints GROUP BY product;

-- 5. Product share by month: join group counts to their monthly totals.
WITH product_counts AS (
    SELECT substr(date_received,1,7) AS month,product,COUNT(*) AS complaints
    FROM complaints GROUP BY 1,2
), month_counts AS (
    SELECT substr(date_received,1,7) AS month,COUNT(*) AS total FROM complaints GROUP BY 1
)
SELECT p.*,m.total,ROUND(100.0*p.complaints/m.total,2) AS share_pct
FROM product_counts p JOIN month_counts m ON p.month=m.month
ORDER BY p.month,p.complaints DESC;

-- 6. Check that normalized text templates do not cross model partitions.
-- These fixed windows match complaint_project.make_splits.
WITH membership AS (
 SELECT text_hash,
 CASE WHEN date_received<='2025-02-09' THEN 'train'
      WHEN date_received<='2025-02-16' THEN 'validation' ELSE 'test' END AS partition_name,
 ROW_NUMBER() OVER(PARTITION BY text_hash ORDER BY date_received,complaint_id) AS rn
 FROM complaints WHERE clean_text IS NOT NULL
)
SELECT text_hash,COUNT(DISTINCT partition_name) AS partitions
FROM membership WHERE rn=1 GROUP BY text_hash HAVING COUNT(DISTINCT partition_name)>1;
