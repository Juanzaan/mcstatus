import sqlite3

conn = sqlite3.connect('data/servers.db')
c = conn.cursor()

# Check total
c.execute('SELECT COUNT(*) FROM server_aliases')
print(f'Total aliases: {c.fetchone()[0]}')

# Check for NeulandSMP
c.execute("SELECT alias_ip, canonical_ip FROM server_aliases WHERE LOWER(alias_ip) = LOWER('NeulandSMP.minehut.gg')")
result = c.fetchone()
print(f'\nNeulandSMP.minehut.gg in table: {result if result else "NOT FOUND"}')

# Show all aliases with "minehut" in name
c.execute("SELECT alias_ip, canonical_ip FROM server_aliases WHERE alias_ip LIKE '%minehut%'")
minehut_aliases = c.fetchall()
print(f'\nMinehut-related aliases ({len(minehut_aliases)}):')
for alias, canonical in minehut_aliases[:5]:
    print(f'  {alias} -> {canonical}')

# Test resolve function
print('\n--- Testing resolve_alias_to_canonical() ---')
from core import database as db
result = db.resolve_alias_to_canonical('NeulandSMP.minehut.gg')
print(f'resolve_alias_to_canonical("NeulandSMP.minehut.gg") = {result}')

conn.close()
