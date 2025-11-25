# Critical Issue: Multiple Minehut Servers Still Show as Canonical

## Problem
Browser test shows 8 Minehut servers visible in dashboard instead of just 1.

## Root Cause
The consolidation script only updated the 12 aliases that were ALREADY in `server_aliases` table. There are MORE Minehut subdomains in the database that:
1. Were never detected as duplicates by DeduplicationEngine
2. Are NOT in `server_aliases` table
3. Still have `is_canonical=1`

## Evidence
- API returns `3mpires.minehut.gg` with `is_canonical=1`
- User reports seeing many `*.minehut.gg` variants when scrolling
- Browser test confirms 8 Minehut servers visible

## Solution
Need to mark ALL `*.minehut.gg` subdomains (except `minehut.gg` itself) as aliases:

```sql
-- Find all Minehut subdomains
SELECT ip FROM servers WHERE ip LIKE '%.minehut.gg%' AND ip != 'minehut.gg';

-- Mark them as aliases
UPDATE servers 
SET is_canonical = 0, canonical_id = 'minehut.gg'
WHERE ip LIKE '%.minehut.gg%' AND ip != 'minehut.gg';

-- Add to server_aliases
INSERT OR IGNORE INTO server_aliases (...) 
SELECT ... FROM servers WHERE ip LIKE '%.minehut.gg%' AND ip != 'minehut.gg';
```

## Next Steps
1. Count total Minehut subdomains
2. Execute mass UPDATE
3. Verify dashboard shows only minehut.gg
