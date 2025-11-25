import sqlite3

conn = sqlite3.connect('data/servers.db')
c = conn.cursor()

# Check if minehut.gg exists as a server
c.execute("SELECT ip, is_canonical FROM servers WHERE ip = 'minehut.gg'")
result = c.fetchone()
print('minehut.gg in servers table:', result if result else 'NOT FOUND')

# Check which canonical servers exist for minehut
c.execute("""
    SELECT DISTINCT canonical_ip 
    FROM server_aliases 
    WHERE canonical_ip LIKE '%minehut%'
""")
print('\nMinehut canonical servers:')
for row in c.fetchall():
    print(f'  {row[0]}')

# Show all aliases of cookiescafe.minehut.gg
c.execute("""
    SELECT alias_ip 
    FROM server_aliases 
    WHERE canonical_ip = 'cookiescafe.minehut.gg'
    ORDER BY alias_ip
""")
print('\nAll aliases pointing to cookiescafe.minehut.gg:')
for row in c.fetchall():
    print(f'  {row[0]}')

conn.close()
