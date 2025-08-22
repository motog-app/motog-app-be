-- Create the database
CREATE DATABASE MOTOG;

-- Create the user with password and LOGIN privilege
CREATE USER MOTOGAdmin WITH PASSWORD 'Jaoba' LOGIN CREATEDB;

-- Grant privileges on the database
GRANT ALL PRIVILEGES ON DATABASE MOTOG TO MOTOGAdmin;

-- Switch to the MOTOG database
\c MOTOG;

-- Grant all privileges on the public schema to the user
GRANT ALL ON SCHEMA public TO MOTOGAdmin;
GRANT USAGE, CREATE ON SCHEMA public TO MOTOGAdmin;

-- Make the user the owner of the schema (optional but recommended)
ALTER SCHEMA public OWNER TO MOTOGAdmin;

-- Ensure that the user has permission to create tables in the public schema
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT ALL ON TABLES TO MOTOGAdmin;




-- Boosts for a single listing
INSERT INTO boost_packages (name, duration_days, price, type) VALUES
('Bronze Boost', 7, 49.00, 'single_listing'),
('Silver Boost', 30, 149.00, 'single_listing'),
('Gold Boost', 90, 399.00, 'single_listing');

-- Bundle boosts that apply to all of a user's listings
INSERT INTO boost_packages (name, duration_days, price, type) VALUES
('Monthly Pro Bundle', 30, 499.00, 'bundle'),
('Quarterly Pro Bundle', 90, 1299.00, 'bundle');