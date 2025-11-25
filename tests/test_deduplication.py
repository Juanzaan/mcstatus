"""
Automated Tests for Deduplication System
-----------------------------------------
Tests for normalization, deduplication logic, and database integrity.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.deduplicate_database import normalize_server_address


class TestNormalization:
    """Test IP/hostname normalization logic."""
    
    def test_case_insensitive(self):
        """Should convert to lowercase."""
        assert normalize_server_address("Play.Hypixel.NET") == "play.hypixel.net"
        assert normalize_server_address("MC.EXAMPLE.COM") == "mc.example.com"
    
    def test_default_port_removal(self):
        """Should remove default Minecraft port :25565."""
        assert normalize_server_address("server.com:25565") == "server.com"
        assert normalize_server_address("192.168.1.1:25565") == "192.168.1.1"
    
    def test_custom_port_preserved(self):
        """Should preserve non-default ports."""
        assert normalize_server_address("server.com:25566") == "server.com:25566"
        assert normalize_server_address("example.com:19132") == "example.com:19132"
    
    def test_whitespace_stripped(self):
        """Should remove leading/trailing whitespace."""
        assert normalize_server_address("  example.com  ") == "example.com"
        assert normalize_server_address("\tserver.com\n") == "server.com"
    
    def test_protocol_removed(self):
        """Should remove protocol prefixes."""
        assert normalize_server_address("minecraft://server.com") == "server.com"
        assert normalize_server_address("mc://example.com") == "example.com"
        assert normalize_server_address("http://server.com") == "server.com"
    
    def test_combined_normalization(self):
        """Should handle multiple normalizations."""
        assert normalize_server_address("  minecraft://Play.SERVER.com:25565  ") == "play.server.com"
    
    def test_empty_input(self):
        """Should handle empty/None input gracefully."""
        assert normalize_server_address("") == ""
        assert normalize_server_address(None) is None
    
    def test_ipv4_preserved(self):
        """Should preserve IPv4 addresses correctly."""
        assert normalize_server_address("192.168.1.1") == "192.168.1.1"
        assert normalize_server_address("10.0.0.1:25565") == "10.0.0.1"


class TestDeduplication:
    """Test deduplication logic (unit tests, no DB required)."""
    
    def test_identify_case_duplicates(self):
        """Should identify case-insensitive duplicates."""
        servers = [
            "play.hypixel.net",
            "Play.Hypixel.NET",
            "PLAY.HYPIXEL.NET"
        ]
        normalized = [normalize_server_address(s) for s in servers]
        assert len(set(normalized)) == 1
    
    def test_identify_port_duplicates(self):
        """Should identify port-redundant duplicates."""
        servers = [
            "example.com",
            "example.com:25565"
        ]
        normalized = [normalize_server_address(s) for s in servers]
        assert len(set(normalized)) == 1
    
    def test_preserve_distinct_servers(self):
        """Should NOT deduplicate truly different servers."""
        servers = [
            "server1.com",
            "server2.com",
            "server1.com:25566"  # Different port
        ]
        normalized = [normalize_server_address(s) for s in servers]
        assert len(set(normalized)) == 3


class TestDatabaseIntegrity:
    """Integration tests requiring SQLite database."""
    
    @pytest.fixture
    def test_db(self, tmp_path):
        """Create a temporary test database."""
        import sqlite3
        db_file = tmp_path / "test_servers.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        
        # Create schema
        cursor.execute("""
            CREATE TABLE servers (
                ip TEXT PRIMARY KEY,
                country TEXT,
                isp TEXT,
                auth_mode TEXT,
                icon TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE server_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER,
                ip TEXT,
                version TEXT,
                online INTEGER,
                max_players INTEGER,
                sample_size INTEGER,
                premium_count INTEGER,
                cracked_count INTEGER,
                new_players INTEGER
            )
        """)
        
        conn.commit()
        yield conn, str(db_file)
        conn.close()
    
    def test_dedup_no_orphaned_snapshots(self, test_db):
        """After deduplication, no orphaned snapshots should exist."""
        conn, db_file = test_db
        cursor = conn.cursor()
        
        # Insert duplicate servers
        cursor.execute("INSERT INTO servers (ip) VALUES ('server.com')")
        cursor.execute("INSERT INTO servers (ip) VALUES ('SERVER.COM')")
        
        # Insert snapshots for both
        cursor.execute("INSERT INTO server_snapshots (scan_id, ip, version, online, max_players, sample_size, premium_count, cracked_count, new_players) VALUES (1, 'server.com', '1.20', 10, 100, 0, 0, 0, 0)")
        cursor.execute("INSERT INTO server_snapshots (scan_id, ip, version, online, max_players, sample_size, premium_count, cracked_count, new_players) VALUES (1, 'SERVER.COM', '1.20', 20, 100, 0, 0, 0, 0)")
        conn.commit()
        
        # Import deduplication logic (would need to adapt for testing)
        from scripts.deduplicate_database import identify_duplicates, merge_and_delete_duplicates
        
        # Run deduplication
        duplicates = identify_duplicates(conn)
        assert len(duplicates) == 1
        
        merge_and_delete_duplicates(conn, duplicates, dry_run=False)
        
        # Verify no orphaned snapshots
        cursor.execute("""
            SELECT COUNT(*) FROM server_snapshots ss
            LEFT JOIN servers s ON ss.ip = s.ip
            WHERE s.ip IS NULL
        """)
        orphaned_count = cursor.fetchone()[0]
        assert orphaned_count == 0, "Orphaned snapshots found after deduplication"
        
        # Verify snapshots were reassigned
        cursor.execute("SELECT COUNT(*) FROM server_snapshots WHERE ip = 'server.com'")
        snapshot_count = cursor.fetchone()[0]
        assert snapshot_count == 2, "Snapshots were not properly reassigned"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
