-- Migration: Fix verification_code column size for hash storage
-- Issue: Email verification service stores 64-char SHA-256 hashes but column is only varchar(10)
-- Solution: Expand verification_code column to varchar(64) to accommodate hashes
-- Created: 2025-09-14
-- Priority: CRITICAL - Blocking user OTP verification

-- Begin transaction for safe migration
BEGIN;

-- Check current column size before migration
SELECT 
    table_name, 
    column_name, 
    data_type, 
    character_maximum_length,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'email_verifications' 
  AND column_name IN ('verification_code', 'otp_hash')
ORDER BY column_name;

-- Show current data that might be affected
SELECT 
    id,
    user_id,
    purpose,
    LENGTH(verification_code) as verification_code_length,
    LENGTH(otp_hash) as otp_hash_length,
    verified,
    created_at
FROM email_verifications
ORDER BY created_at DESC;

-- Expand verification_code column from varchar(10) to varchar(64)
-- This allows storage of both 6-digit codes (existing) and 64-char hashes (new)
ALTER TABLE email_verifications 
ALTER COLUMN verification_code TYPE character varying(64);

-- Verify the column change was successful
SELECT 
    table_name, 
    column_name, 
    data_type, 
    character_maximum_length,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'email_verifications' 
  AND column_name = 'verification_code';

-- Commit the transaction
COMMIT;

-- Success message
SELECT 'Migration completed successfully: verification_code column expanded to varchar(64)' as status;