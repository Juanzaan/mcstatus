#!/usr/bin/env python3
"""Fix database.py imports"""

import os

DB_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'servers.db')

# Read current file
with open('../core/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports at the beginning
imports = """import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import requests
import time
import os

"""

# Write fixed file
with open('../core/database.py', 'w', encoding='utf-8') as f:
    f.write(imports + content)

print("✅ Fixed database.py imports")
