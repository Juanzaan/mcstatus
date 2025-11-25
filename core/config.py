"""
Configuration management for the Minecraft Server Dashboard.
Loads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# API Configuration
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '5000'))
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

# Data Configuration
DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / 'data'))
UNIFIED_SERVERS_FILE = DATA_DIR / 'unified_servers.json'

# Scheduler Configuration
SCHEDULER_ENABLED = os.getenv('SCHEDULER_ENABLED', 'True').lower() in ('true', '1', 'yes')
REFRESH_INTERVAL_MINUTES = int(os.getenv('REFRESH_INTERVAL_MINUTES', '30'))
FULL_SCAN_INTERVAL_HOURS = int(os.getenv('FULL_SCAN_INTERVAL_HOURS', '6'))

# CORS Configuration (for production, restrict this)
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

# Pagination defaults
DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', '50'))
MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', '200'))

def validate_config():
    """Validate critical configuration values"""
    errors = []
    
    # Validate Port
    if not (1 <= API_PORT <= 65535):
        errors.append(f"API_PORT must be between 1 and 65535, got {API_PORT}")
        
    # Validate Refresh Intervals
    if REFRESH_INTERVAL_MINUTES < 1:
        errors.append(f"REFRESH_INTERVAL_MINUTES must be >= 1, got {REFRESH_INTERVAL_MINUTES}")
        
    # Validate Data Directory
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create DATA_DIR at {DATA_DIR}: {e}")
            
    if errors:
        raise ValueError("Configuration Error(s):\n" + "\n".join(errors))

# Run validation on import
try:
    validate_config()
except ValueError as e:
    print(f"❌ {e}")
    # We don't exit here to allow importing for docs generation, 
    # but in production this will be caught early.
