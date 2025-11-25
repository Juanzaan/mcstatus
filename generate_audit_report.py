"""Generate audit report to text file"""
import sqlite3
from collections import defaultdict

DB_FILE = 'data/servers.db'

def extract_root_domain(hostname):
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    parts = hostname.split('.')
    if len(parts) <= 2:
        return hostname
    return '.'.join(parts[-2:])

def calculate_domain_score(hostname):
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    dot_count = hostname.count('.')
    length = len(hostname)
    score = -(dot_count * 10000) - (length * 100)
    return score

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("SELECT ip FROM servers WHERE is_canonical = 1 ORDER BY ip")
canonical_servers = [row[0] for row in cursor.fetchall()]

# Group by root domain
root_groups = defaultdict(list)
for server in canonical_servers:
    root = extract_root_domain(server)
    root_groups[root].append(server)

# Find conflicts
conflicts = []
for root, servers in root_groups.items():
    if len(servers) > 1:
        scored_servers = []
        for server in servers:
            score = calculate_domain_score(server)
            scored_servers.append((server, score))
        scored_servers.sort(key=lambda x: x[1], reverse=True)
        master_candidate = scored_servers[0]
        aliases_candidates = scored_servers[1:]
        conflicts.append({
            'root_domain': root,
            'master': master_candidate[0],
            'master_score': master_candidate[1],
            'aliases': [(ip, score) for ip, score in aliases_candidates],
            'score_differences': [master_candidate[1] - score for _, score in aliases_candidates]
        })

# Write report
with open('audit_report_clean.txt', 'w', encoding='utf-8') as f:
    f.write("ROOT VS SUBDOMAIN AUDIT REPORT\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Total canonical servers: {len(canonical_servers)}\n")
    f.write(f"Root domains with conflicts: {len(conflicts)}\n\n")
    
    if conflicts:
        f.write("CONFLICTS DETECTED:\n")
        f.write("=" * 80 + "\n\n")
        
        for i, conflict in enumerate(conflicts, 1):
            f.write(f"{i}.Root Domain: {conflict['root_domain']}\n")
            f.write(f"   Master Candidate: {conflict['master']} (score: {conflict['master_score']})\n")
            f.write(f"   Aliases to consolidate:\n")
            for j, ((alias_ip, alias_score), score_diff) in enumerate(zip(conflict['aliases'], conflict['score_differences']), 1):
                f.write(f"      {j}) {alias_ip:40} (score: {alias_score:6}, diff: +{score_diff})\n")
            f.write("\n")
        
        total_aliases = sum(len(c['aliases']) for c in conflicts)
        f.write("=" * 80 + "\n")
        f.write(f"SUMMARY:\n")
        f.write(f"  Total conflicts: {len(conflicts)}\n")
        f.write(f"  Servers to consolidate: {total_aliases}\n")
        f.write(f"  Canonical count after fix: {len(canonical_servers) - total_aliases}\n")
    else:
        f.write("NO CONFLICTS DETECTED!\n")
        f.write("Database is clean.\n")

conn.close()
print("Report generated: audit_report_clean.txt")
