# Issue Summary: Popular Servers Not Appearing

## Problem Identified

**Root Cause**: Popular servers (Hypixel, Minehut, Universocraft, etc.) were added to the `servers` table with `alternate_ips`, but they don't have entries in `server_snapshots` table.

**Impact**: 
- API query uses `JOIN server_snapshots` which filters out servers without recent snapshots
- Result: Popular servers invisible in dashboard
- Hypixel search returns 0 results
- Minehut found but no alternate IPs showing

## Technical Details

### Current Database State
```sql
SELECT COUNT(*) FROM servers WHERE ip IN ('mc.hypixel.net', 'minehut.com', 'universocraft.com');
-- Result: 3 (servers exist)

SELECT COUNT(*) FROM server_snapshots WHERE ip IN ('mc.hypixel.net', 'minehut.com', 'universocraft.com');
-- Result: 0 (NO snapshots)
```

### API Query (database.py line 237)
```python
SELECT s.ip, s.alternate_ips, ss.online, ss.max_players
FROM servers s
JOIN server_snapshots ss ON s.ip = ss.ip  # <-- FILTERS OUT servers without snapshots
WHERE ss.scan_id = (SELECT MAX(scan_id) FROM scans)
```

## Solution Options

### Option 1: Quick Scan (Recommended)
**What**: Scan only the 20 popular servers just added  
**Time**: 1-2 minutes  
**Impact**: High-value servers immediately visible

**Servers to scan**:
- mc.hypixel.net
- minehut.com
- universocraft.com
- play.cubecraft.net
- play.hivemc.com
- us.mineplex.com
- 2b2t.org
- play.wynncraft.com
- ... (14 more)

### Option 2: Full Rescan
**What**: Rescan all 5,744 servers  
**Time**: 10-15 minutes  
**Impact**: Everything updated

### Option 3: Modify API Query (Not Recommended)
**What**: Change `JOIN` to `LEFT JOIN` to show unverified servers  
**Problem**: Would show offline/unverified servers as if they're active

## Next Steps

**Immediate**:
1. Run `scripts/scan_and_verify.py --limit 100` (currently running)
2. This will scan top 100 servers including popular ones
3. Wait ~3-5 minutes for completion

**After Scan**:
1. Refresh dashboard
2. Search for "hypixel" - should find mc.hypixel.net
3. Click to expand - should show alternate IPs
4. Verify UI expansion working

## Files Reference
- `scripts/add_popular_servers.py` - Script that added servers
- `core/database.py:231` - get_latest_scan_data() with JOIN
- `web/static/dashboard.js:347` - alternates expansion logic
