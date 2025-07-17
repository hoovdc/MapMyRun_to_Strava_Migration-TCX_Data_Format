import os
import logging
from dotenv import load_dotenv
from src.mmr_downloader import MmrDownloader
from src.tcx_validator import TcxValidator
from utils.logger import setup_logger
from src.database_manager import DatabaseManager, Workout
from src.csv_parser import WorkoutInventory
from tqdm import tqdm
import time

def main():
    """
    Main function to run the MapMyRun to Strava migration process.
    """
    # Load environment variables from .env file
    load_dotenv(dotenv_path='config/.env')
    
    # Set up logging
    setup_logger()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting MapMyRun to Strava Migration.")

    # --- Initialize Database and CSV Parser ---
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    # Populate database from CSV if it's empty
    if session.query(Workout).count() == 0:
        logger.info("Database is empty. Populating from CSV...")
        csv_path = 'data/From_MapMyRun/CSV_for_event_ID_extraction/user16881_workout_history.csv'
        inventory = WorkoutInventory(csv_path)
        workouts_data = inventory.extract_workouts()
        
        if workouts_data:
            for workout_data in workouts_data:
                workout = Workout(**workout_data)
                session.add(workout)
            session.commit()
            logger.info(f"Successfully populated database with {len(workouts_data)} workouts.")
        else:
            logger.error("No workouts extracted from CSV. Halting.")
            session.close()
            return
    else:
        logger.info("Database already contains data. Skipping CSV population.")
    
    # --- Download and Validate all pending workouts ---
    # Fetching the next 100 pending workouts for a controlled test run.
    pending_workouts = session.query(Workout).filter(Workout.status == 'pending').limit(100).all()
    
    if not pending_workouts:
        logger.info("No pending workouts to download. All workouts are processed.")
    else:
        logger.info(f"--- Starting full download and validation of {len(pending_workouts)} pending workouts ---")
        cookie_string = os.getenv("MAPMYRUN_COOKIE_STRING")
        if not cookie_string or cookie_string == 'paste_your_full_cookie_string_here':
            logger.error("MAPMYRUN_COOKIE_STRING is not set in config/.env.")
            session.close()
            return
            
        downloader = MmrDownloader(cookie_string=cookie_string)
        validator = TcxValidator()
        
        successful_downloads = 0
        failed_downloads = 0

        with tqdm(total=len(pending_workouts), desc="Processing Workouts") as pbar:
            for workout in pending_workouts:
                downloaded_path = downloader.download_tcx(workout.workout_id)
                
                if downloaded_path:
                    workout.status = 'downloaded'
                    if validator.validate(str(downloaded_path)):
                        workout.status = 'validated'
                        workout.download_path = str(downloaded_path)
                        successful_downloads += 1
                    else:
                        workout.status = 'failed'
                        failed_downloads += 1
                else:
                    workout.status = 'failed'
                    failed_downloads += 1
                
                session.commit() # Commit after each workout to save progress
                pbar.update(1)
                
                # Don't sleep after the last download in the batch
                if pending_workouts.index(workout) < len(pending_workouts) - 1:
                    time.sleep(2) # Polite delay
        
        logger.info(f"Batch process complete. Successful: {successful_downloads}, Failed: {failed_downloads}.")
            
    session.close()
    logger.info("Migration script finished.")


if __name__ == "__main__":
    main()
