-- Migration 001: Add Deduplication Fingerprinting Fields
-- Date: 2025-11-22
-- Purpose: Support unified deduplication engine with canonical/alias system

-- Add fingerprinting columns to servers table
ALTER TABLE servers ADD COLUMN favicon_hash TEXT;
ALTER TABLE servers ADD COLUMN canonical_id TEXT REFERENCES servers(ip);
ALTER TABLE servers ADD COLUMN is_canonical BOOLEAN DEFAULT 1;
ALTER TABLE servers ADD COLUMN resolved_ip TEXT;
ALTER TABLE servers ADD COLUMN last_dns_check DATETIME;

-- Create server_aliases table for tracking duplicate relationships
CREATE TABLE IF NOT EXISTS server_aliases (
    alias_ip TEXT PRIMARY KEY,
    canonical_ip TEXT NOT NULL,
    detection_method TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (canonical_ip) REFERENCES servers(ip) ON DELETE CASCADE,
    FOREIGN KEY (alias_ip) REFERENCES servers(ip) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_servers_canonical_id ON servers(canonical_id);
CREATE INDEX IF NOT EXISTS idx_servers_favicon_hash ON servers(favicon_hash);
CREATE INDEX IF NOT EXISTS idx_servers_resolved_ip ON servers(resolved_ip);
CREATE INDEX IF NOT EXISTS idx_servers_is_canonical ON servers(is_canonical);
CREATE INDEX IF NOT EXISTS idx_aliases_canonical ON server_aliases(canonical_ip);

-- Migration complete
