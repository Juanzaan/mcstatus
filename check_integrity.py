import sqlite3
conn = sqlite3.connect('data/servers.db')
c = conn.cursor()
print('=== DATABASE INTEGRITY CHECK ===')
c.execute('PRAGMA integrity_check')
print(f'Integrity: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM servers')
print(f'Total servers: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM servers WHERE ip IS NULL OR ip = ""')
print(f'Servers with NULL/empty IP: {c.fetchone()[0]}')
c.execute('SELECT COUNT(DISTINCT ip) FROM servers')
distinct = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM servers')
total = c.fetchone()[0]
print(f'Duplicate IPs: {total - distinct}')
c.execute('SELECT COUNT(*) FROM server_snapshots WHERE ip NOT IN (SELECT ip FROM servers)')
print(f'Orphaned snapshots: {c.fetchone()[0]}')
