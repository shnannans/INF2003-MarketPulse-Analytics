#!/usr/bin/env python3
"""
Automated Scheduler for Financial Data Collection
Runs data collection at specified intervals
Adheres to API limitation and market hours
"""

import schedule
import time
import subprocess
import logging
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SmartFinancialScheduler:
    def __init__(self):
        # Fix: Use correct script name
        self.script_path = os.path.join(os.path.dirname(__file__), 'local_data_collection.py')
        
        # Verify script exists
        if not os.path.exists(self.script_path):
            logger.error(f"Data collection script not found: {self.script_path}")
            raise FileNotFoundError(f"Script not found: {self.script_path}")
        
        self.last_successful_run = None
        self.consecutive_failures = 0
        self.max_retries = 3
        
    def is_market_day(self):
        """Check if today is a market day (weekday, not holiday)"""
        today = datetime.now()
        # Monday = 0, Sunday = 6
        return today.weekday() < 5  # Monday through Friday
    
    def is_market_hours(self):
        """Check if current time is during market hours (9 AM - 4 PM ET)"""
        now = datetime.now()
        market_open = now.replace(hour=9, minute=0, second=0)
        market_close = now.replace(hour=16, minute=0, second=0)
        return market_open <= now <= market_close
        
    def run_data_collection(self, collection_type="full"):
        """Run the data collection script with retry logic"""
        try:
            logger.info(f"Starting {collection_type} data collection...")
            
            # Run with timeout and proper error handling
            result = subprocess.run([
                sys.executable, self.script_path
            ], capture_output=True, text=True, timeout=3600)  # 1 hour timeout
            
            if result.returncode == 0:
                logger.info("Data collection completed successfully")
                logger.debug(f"Output: {result.stdout}")
                self.last_successful_run = datetime.now()
                self.consecutive_failures = 0
                return True
            else:
                logger.error(f"Data collection failed with return code {result.returncode}")
                logger.error(f"Error output: {result.stderr}")
                self.consecutive_failures += 1
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Data collection timed out after 1 hour")
            self.consecutive_failures += 1
            return False
        except Exception as e:
            logger.error(f"Error running data collection: {e}")
            self.consecutive_failures += 1
            return False
    
    def run_with_retry(self, collection_type="full"):
        """Run data collection with retry logic"""
        for attempt in range(self.max_retries):
            if self.run_data_collection(collection_type):
                return True
            
            if attempt < self.max_retries - 1:
                wait_time = (attempt + 1) * 10  # 10, 20, 30 seconds
                logger.info(f"Retrying in {wait_time} seconds... (attempt {attempt + 2}/{self.max_retries})")
                time.sleep(wait_time)
        
        logger.error(f"Data collection failed after {self.max_retries} attempts")
        return False
    
    def market_day_collection(self):
        """Run collection only on market days"""
        if self.is_market_day():
            self.run_with_retry("market_hours")
        else:
            logger.info("Skipping collection - market closed (weekend/holiday)")
    
    def setup_smart_schedule(self):
        """Setup a more intelligent collection schedule"""
        # Daily comprehensive collection at 6 AM (before market opens)
        schedule.every().day.at("06:00").do(self.run_with_retry, "pre_market")
        
        # Market hours collection - only twice per day to respect API limits
        schedule.every().monday.at("10:00").do(self.market_day_collection)
        schedule.every().monday.at("14:00").do(self.market_day_collection)
        schedule.every().tuesday.at("10:00").do(self.market_day_collection)
        schedule.every().tuesday.at("14:00").do(self.market_day_collection)
        schedule.every().wednesday.at("10:00").do(self.market_day_collection)
        schedule.every().wednesday.at("14:00").do(self.market_day_collection)
        schedule.every().thursday.at("10:00").do(self.market_day_collection)
        schedule.every().thursday.at("14:00").do(self.market_day_collection)
        schedule.every().friday.at("10:00").do(self.market_day_collection)
        schedule.every().friday.at("14:00").do(self.market_day_collection)
        
        # Post-market collection at 5 PM on market days
        schedule.every().monday.at("17:00").do(self.market_day_collection)
        schedule.every().tuesday.at("17:00").do(self.market_day_collection)
        schedule.every().wednesday.at("17:00").do(self.market_day_collection)
        schedule.every().thursday.at("17:00").do(self.market_day_collection)
        schedule.every().friday.at("17:00").do(self.market_day_collection)
        
        # Weekend news update (once per day, lighter load)
        schedule.every().saturday.at("09:00").do(self.run_with_retry, "news_only")
        schedule.every().sunday.at("09:00").do(self.run_with_retry, "news_only")
        
        logger.info("Smart schedule configured:")
        logger.info("- Daily comprehensive: 6:00 AM")
        logger.info("- Market days: 10:00 AM, 2:00 PM, 5:00 PM")
        logger.info("- Weekend news: 9:00 AM Saturday & Sunday")
        logger.info("- Automatic retry logic enabled")
    
    def health_check(self):
        """Check scheduler health"""
        if self.consecutive_failures >= 5:
            logger.warning("Multiple consecutive failures detected - scheduler may need attention")
        
        if self.last_successful_run:
            time_since_success = datetime.now() - self.last_successful_run
            if time_since_success > timedelta(days=2):
                logger.warning(f"No successful collection in {time_since_success}")
    
    def run_scheduler(self):
        """Run the improved scheduler with health monitoring"""
        logger.info("Starting Smart Financial Data Collection Scheduler...")
        logger.info(f"Using script: {self.script_path}")
        
        self.setup_smart_schedule()
        
        # Run initial collection if it's been more than 12 hours
        logger.info("Running initial health check and data collection...")
        if self.run_with_retry("initial"):
            logger.info("Initial collection successful - scheduler ready")
        else:
            logger.warning("Initial collection failed - scheduler will continue with scheduled runs")
        
        # Main scheduler loop with health monitoring
        try:
            while True:
                schedule.run_pending()
                
                # Health check every hour
                if datetime.now().minute == 0:
                    self.health_check()
                
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise

def main():
    """Main function with better error handling"""
    try:
        scheduler = SmartFinancialScheduler()
        scheduler.run_scheduler()
    except FileNotFoundError as e:
        logger.error(f"Setup error: {e}")
        logger.error("Make sure 'local_data_collection.py' exists in the same directory")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()