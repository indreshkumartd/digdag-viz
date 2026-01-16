INSERT INTO golden.segment_summary
SELECT
  region,
  COUNT(*) AS total_events
FROM staging.analysis_prep
GROUP BY region;
