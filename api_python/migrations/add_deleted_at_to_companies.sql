-- Migration: Add deleted_at column to companies table for soft delete functionality
-- This migration adds the deleted_at column to support soft deletes

ALTER TABLE companies 
ADD COLUMN deleted_at DATETIME NULL 
AFTER created_at;

-- Add index on deleted_at for better query performance when filtering out deleted records
CREATE INDEX idx_companies_deleted_at ON companies(deleted_at);

-- Set all existing records to have deleted_at = NULL (not deleted)
UPDATE companies SET deleted_at = NULL WHERE deleted_at IS NULL;

