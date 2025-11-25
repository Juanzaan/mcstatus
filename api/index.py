import sys
import os
from pathlib import Path

# Add the project root to sys.path
# This allows importing from web.server and ensures web/server.py can find core modules
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from web.server import app

# Vercel expects the 'app' object to be available
