"""Automated Data Refresh Scheduler for the Mutual Fund FAQ Assistant."""

import sys
import logging
from pathlib import Path
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler

# Ensure the src directory is in the system path to allow imports
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import ingest
import retrieval

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)

def refresh_data_pipeline():
    """Runs the data ingestion and index rebuilding pipeline."""
    logging.info("Starting automated daily data refresh...")
    
    try:
        # Step 1: Ingest latest data
        logging.info(f"Fetching latest data from {len(ingest.SOURCE_URLS)} sources...")
        ingest.ingest_sources(ingest.SOURCE_URLS)
        logging.info("Data ingestion completed successfully.")
        
        # Step 2: Clear old index and rebuild
        logging.info("Clearing old vector index and rebuilding...")
        try:
            retrieval.client.delete_collection(name="mutual_fund_facts")
            logging.info("Old collection deleted.")
        except Exception as e:
            logging.warning(f"Could not delete old collection (might not exist): {e}")
            
        # Re-initialize collection reference in the retrieval module and build
        retrieval.collection = retrieval.client.get_or_create_collection(name="mutual_fund_facts")
        retrieval.build_index()
        logging.info("Vector index rebuilt successfully.")
        
        logging.info("Daily data refresh completed without errors.")
    except Exception as e:
        logging.error(f"Data refresh pipeline failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run-once":
        refresh_data_pipeline()
        sys.exit(0)
        
    ist_tz = pytz.timezone('Asia/Kolkata')
    scheduler = BlockingScheduler(timezone=ist_tz)
    
    # Schedule the job to run every day at 10:00 AM IST
    scheduler.add_job(refresh_data_pipeline, 'cron', hour=10, minute=0)
    
    logging.info("Scheduler started. Waiting for the next run at 10:00 AM IST...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stopped.")
