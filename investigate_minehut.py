import sqlite3

conn = sqlite3.connect('data/servers.db')
c = conn.cursor()

# Check minehut.gg fingerprint
c.execute("""
    SELECT ip, favicon_hash, resolved_ip, is_canonical
    FROM servers
    WHERE ip = 'minehut.gg'
""")
minehut_main = c.fetchone()
print('minehut.gg fingerprint:')
if minehut_main:
    print(f'  IP: {minehut_main[0]}')
    print(f'  Favicon hash: {minehut_main[1]}')
    print(f'  Resolved IP: {minehut_main[2]}')
    print(f'  Is canonical: {minehut_main[3]}')
else:
    print('  NOT FOUND')

# Check cookiescafe.minehut.gg fingerprint
c.execute("""
    SELECT ip, favicon_hash, resolved_ip, is_canonical
    FROM servers
    WHERE ip = 'cookiescafe.minehut.gg'
""")
cookiescafe = c.fetchone()
print('\ncookiescafe.minehut.gg fingerprint:')
if cookiescafe:
    print(f'  IP: {cookiescafe[0]}')
    print(f'  Favicon hash: {cookiescafe[1]}')
    print(f'  Resolved IP: {cookiescafe[2]}')
    print(f'  Is canonical: {cookiescafe[3]}')

# Check if they match
if minehut_main and cookiescafe:
    print('\n=== COMPARISON ===')
    print(f'Same favicon: {minehut_main[1] == cookiescafe[1]}')
    print(f'Same resolved IP: {minehut_main[2] == cookiescafe[2]}')
    
    if minehut_main[1] == cookiescafe[1] or minehut_main[2] == cookiescafe[2]:
        print('\n✅ They ARE duplicates but not merged!')
        print('Solution: Manual UPDATE needed')
    else:
        print('\n⚠️  They are NOT duplicates (different servers)')
        print('Solution: Keep as separate')

conn.close()
