-- Migration: add advisory_summary to yield_records
-- Run once against the PostgreSQL database.

ALTER TABLE yield_records ADD COLUMN IF NOT EXISTS advisory_summary TEXT;
