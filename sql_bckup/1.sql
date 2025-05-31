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