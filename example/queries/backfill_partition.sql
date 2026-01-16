INSERT INTO staging.backfill_partitions
SELECT
  *
FROM src_raw.events
WHERE event_date = '{{ session_date }}';
