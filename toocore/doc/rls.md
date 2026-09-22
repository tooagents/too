2.2     check rls enabled?
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

SELECT relname, relrowsecurity
FROM pg_class
WHERE relname = 'products';




sudo -u postgres psql




-- Create user
CREATE USER uxai WITH PASSWORD 'pxai';

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO uxai;

-- Set default privileges for FUTURE tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT ALL ON TABLES TO uxai;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT ALL ON SEQUENCES TO uxai;

-- Grant privileges on EXISTING tables (notes and users)
GRANT ALL ON ALL TABLES IN SCHEMA public TO uxai;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO uxai;



