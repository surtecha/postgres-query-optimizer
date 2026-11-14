CREATE ROLE pgo_reader LOGIN PASSWORD 'local_reader_only' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE pgo_experiment LOGIN PASSWORD 'local_experiment_only' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE pgo_benchmark OWNER pgo_experiment;
\connect pgo_benchmark
REVOKE ALL ON DATABASE pgo_benchmark FROM PUBLIC;
GRANT CONNECT ON DATABASE pgo_benchmark TO pgo_reader, pgo_experiment;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE SCHEMA commerce AUTHORIZATION pgo_experiment;
CREATE SCHEMA edge_cases AUTHORIZATION pgo_experiment;
GRANT USAGE ON SCHEMA commerce, edge_cases TO pgo_reader;
ALTER ROLE pgo_reader SET default_transaction_read_only = on;
ALTER ROLE pgo_reader SET statement_timeout = '30s';
ALTER ROLE pgo_reader SET lock_timeout = '1s';
ALTER ROLE pgo_reader SET search_path = pg_catalog, commerce;
ALTER ROLE pgo_reader SET work_mem = '16MB';
ALTER ROLE pgo_experiment SET search_path = pg_catalog, commerce;
ALTER DEFAULT PRIVILEGES FOR ROLE pgo_experiment IN SCHEMA commerce GRANT SELECT ON TABLES TO pgo_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE pgo_experiment IN SCHEMA edge_cases GRANT SELECT ON TABLES TO pgo_reader;
