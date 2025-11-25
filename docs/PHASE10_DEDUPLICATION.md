# Phase 10: Unified Deduplication Engine

## Overview
Complete deduplication system with multi-strategy detection, canonical/alias relationships, and intelligent merging.

## User Decisions Implemented

✅ **Favicon Storage**: Hashes only for aliases, full base64 only in canonical servers  
✅ **DNS Cache**: 48-hour TTL  
✅ **Alias Visibility**: Hidden in public frontend, searchable, admin view with collapsible details  
✅ **Migration Path**: Schema → Enrichment → Dry-Run → Merge

---

## Execution Steps

### Step 1: Apply Database Migration

```bash
python scripts/migrations/run_migrations.py
```

**What it does:**
- Adds `favicon_hash`, `canonical_id`, `is_canonical`, `resolved_ip`, `last_dns_check` to `servers` table
- Creates `server_aliases` table
- Creates indexes for performance

---

### Step 2: Run Enrichment Scanner

```bash
python scripts/enrichment_scanner.py
```

**What it does:**
- Generates SHA256 hashes for all existing favicons
- Resolves DNS for all servers (rate-limited to 10/sec)
- Populates the new fingerprint fields

**Expected runtime**: ~5-10 minutes for 643 servers

---

### Step 3: Analyze Duplicates (Dry-Run)

```bash
python scripts/master_dedup.py --mode dry-run --output dedup_report.json
```

**What it does:**
- Runs all 3 detection strategies
- Generates JSON report with confidence scores
- **NO database changes**

**Review the report** before proceeding!

---

### Step 4: Auto-Merge High-Confidence Matches

```bash
python scripts/master_dedup.py --mode auto --threshold 0.9
```

**What it does:**
- Merges only matches with ≥90% confidence
- Creates entries in `server_aliases` table
- Updates `canonical_id` and `is_canonical` flags

---

## Detection Strategies

| Strategy | Confidence | Trigger |
|----------|-----------|---------|
| **DNS Resolution** | 100% | Same resolved IP address |
| **Favicon + Players** | 85% | Same favicon hash + player count within 5% |
| **String Normalization** | 70% | Aggressive text normalization |

---

## Files Created

### Core
- `core/deduplication_engine.py` - Main service class

### Scripts
- `scripts/migrations/001_add_dedup_fields.sql` - DB schema changes
- `scripts/migrations/run_migrations.py` - Migration runner
- `scripts/enrichment_scanner.py` - Fingerprint populator
- `scripts/master_dedup.py` - Unified CLI

### Legacy (Deprecated)
- `scripts/deduplicate_database.py` → Use `master_dedup.py` instead
- `scripts/fix_duplicates_cleanup.py` → Use `master_dedup.py` instead
- `scripts/aggressive_dedup.py` → Use `master_dedup.py` instead

---

## Troubleshooting

**DNS resolution fails**: Check internet connection, some servers may timeout  
**Migration error**: Ensure no other processes are using `servers.db`  
**Low match count**: Run enrichment scanner first to populate fingerprints

---

## Next Steps (Future)

- [ ] Integrate canonical resolution into `/api/servers` endpoint
- [ ] Add admin UI for viewing/managing aliases
- [ ] Implement player sample matching (requires schema extension)
- [ ] Add MOTD fuzzy matching strategy
