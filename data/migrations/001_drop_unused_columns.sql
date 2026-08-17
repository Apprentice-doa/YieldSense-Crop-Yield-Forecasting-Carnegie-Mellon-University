-- Migration: drop unused columns
-- Run once against the Neon PostgreSQL database.

ALTER TABLE farmer_sessions
    DROP COLUMN IF EXISTS token_type;

ALTER TABLE conversations
    DROP COLUMN IF EXISTS description,
    DROP COLUMN IF EXISTS context_data;

ALTER TABLE messages
    DROP COLUMN IF EXISTS message_type,
    DROP COLUMN IF EXISTS is_read,
    DROP COLUMN IF EXISTS updated_at;
