"""
Enterprise Scheduler
--------------------
Automates scanning and scraping tasks using APScheduler.
Features:
- Periodic execution of scrapers and verifiers.
- Startup library version check.
- Graceful shutdown.
"""

import time
import logging
import sys
import os
import subprocess
from datetime import datetime

# Ensure core modules are importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_loader import ConfigLoader
from core.logger import setup_logger

# Auto-install APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError:
    print("Installing APScheduler...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "apscheduler"])
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

# Setup Logger
os.makedirs("logs", exist_ok=True)
logger = setup_logger("Scheduler", "logs/scheduler.log")

def check_library_versions():
    """Check for updates to critical libraries"""
    logger.info("🔍 Checking library versions...")
    libraries = ['mcstatus', 'cloudscraper', 'apscheduler', 'psutil']
    
    for lib in libraries:
        try:
            # Get installed version
            result = subprocess.check_output([sys.executable, "-m", "pip", "show", lib], text=True)
            version = None
            for line in result.split('\n'):
                if line.startswith('Version: '):
                    version = line.split(' ')[1]
                    break
            
            logger.info(f"📦 {lib}: {version} (Installed)")
            
            # In a real enterprise app, we might query PyPI here to check for updates
            # For now, we just log the current version to ensure visibility
            
        except subprocess.CalledProcessError:
            logger.warning(f"⚠️ {lib} is NOT installed!")

def run_scanner_job():
    """Job: Run the main scanner"""
    logger.info("⏰ Starting Scheduled Scan Job...")
    try:
        # Run scan_and_verify.py as a subprocess to ensure clean state
        cmd = [sys.executable, "scripts/scan_and_verify.py", "--input", "data/unified_servers.json", "--tags", "scheduled"]
        subprocess.run(cmd, check=True)
        logger.info("✅ Scheduled Scan Job Completed.")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Scheduled Scan Job Failed: {e}")

def run_scraper_job():
    """Job: Run the cloudflare scraper"""
    logger.info("⏰ Starting Scheduled Scraper Job...")
    try:
        cmd = [sys.executable, "scrapers/cloudflare_bypass_scraper.py"]
        subprocess.run(cmd, check=True)
        logger.info("✅ Scheduled Scraper Job Completed.")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Scheduled Scraper Job Failed: {e}")

def start_scheduler():
    check_library_versions()
    
    scheduler = BackgroundScheduler()
    
    # Schedule Scanner (e.g., every 6 hours)
    scheduler.add_job(
        run_scanner_job,
        trigger=IntervalTrigger(hours=6),
        id='scanner_job',
        name='Full Server Scan',
        replace_existing=True
    )
    
    # Schedule Scraper (e.g., every 2 hours)
    scheduler.add_job(
        run_scraper_job,
        trigger=IntervalTrigger(hours=2),
        id='scraper_job',
        name='Cloudflare Scraper',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("🚀 Scheduler started. Press Ctrl+C to exit.")
    
    # Print jobs
    scheduler.print_jobs()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Stopping scheduler...")
        scheduler.shutdown()

if __name__ == "__main__":
    start_scheduler()
