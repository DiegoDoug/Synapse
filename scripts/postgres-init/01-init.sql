-- Postgres cluster initialization for Synapse (Stage 8).
-- Runs ONCE, only when the data directory is first created (docker-entrypoint
-- semantics). Idempotent statements so a manual re-run is safe.

-- pg_stat_statements powers the index/performance audit: it records normalized
-- query stats so slow queries and missing indexes can be found post-deploy via
--   SELECT query, calls, mean_exec_time FROM pg_stat_statements
--   ORDER BY mean_exec_time DESC LIMIT 20;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Trigram index support for ILIKE/text search on synced email/document content.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Conservative connection guard. The app pool (DB_POOL_SIZE + overflow) plus
-- the worker must stay under this. Raise alongside instance sizing.
ALTER SYSTEM SET max_connections = '100';
