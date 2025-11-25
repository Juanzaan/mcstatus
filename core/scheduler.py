"""
Background Scheduler for Minecraft Server Status
Handles automated scanning and data refreshing.
"""
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.server_merger import merge_all_servers
from scrapers.fast_scanner import FastScanner
from core.priority_scanner import run_priority_scan

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Scheduler")

class SchedulerManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.last_run = {
            'refresh_status': None,
            'full_scan': None,
            'priority_scan': None
        }
        self.is_running = False
        
    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            # Job 0: Priority Scan for Popular Servers (every 5 minutes)
            self.scheduler.add_job(
                func=self.run_priority_scan_job,
                trigger=IntervalTrigger(minutes=5),
                id='priority_scan',
                name='Priority Server Scan',
                replace_existing=True
            )

            # Job 1: Refresh online status of known servers (every 30 minutes)
            self.scheduler.add_job(
                func=self.refresh_server_status,
                trigger=IntervalTrigger(minutes=30),
                id='refresh_status',
                name='Refresh Server Status',
                replace_existing=True
            )
            
            # Job 2: Full merge and cleanup (every 6 hours)
            self.scheduler.add_job(
                func=self.run_full_merge,
                trigger=IntervalTrigger(hours=6),
                id='full_scan',
                name='Full Server Merge',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("Scheduler started")
            
    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")
            
    def refresh_server_status(self):
        """Quickly refresh status of currently known servers"""
        logger.info("Starting scheduled status refresh...")
        try:
            # For now, we'll just run the merger which updates stats
            # In the future, this could run a lightweight scanner on known IPs
            merge_all_servers()
            self.last_run['refresh_status'] = datetime.now().isoformat()
            logger.info("Status refresh complete")
        except Exception as e:
            logger.error(f"Error in status refresh: {e}")
            
    def run_full_merge(self):
        """Run a full merge of all data sources"""
        logger.info("Starting scheduled full merge...")
        try:
            merge_all_servers()
            self.last_run['full_scan'] = datetime.now().isoformat()
            logger.info("Full merge complete")
        except Exception as e:
            logger.error(f"Error in full merge: {e}")

    def run_priority_scan_job(self):
        """Run priority scan for popular servers"""
        logger.info("Starting scheduled priority scan...")
        try:
            import asyncio
            asyncio.run(run_priority_scan())
            self.last_run['priority_scan'] = datetime.now().isoformat()
            logger.info("Priority scan complete")
        except Exception as e:
            logger.error(f"Error in priority scan: {e}")
            
    def get_status(self):
        """Get current scheduler status"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None
            })
            
        return {
            'running': self.is_running,
            'jobs': jobs,
            'last_run': self.last_run
        }

# Global instance
scheduler_manager = SchedulerManager()
