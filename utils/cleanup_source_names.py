import sys
import os
import logging
from tqdm import tqdm

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database_manager import DatabaseManager, Workout
from utils.logger import setup_logger

def cleanup_sources():
    """
    Connects to the database and standardizes the 'Source' part of the
    activity_name for all workouts.
    """
    setup_logger(level=logging.INFO)
    logger = logging.getLogger(__name__)

    db_manager = DatabaseManager()
    session = db_manager.get_session()

    # Define the mapping of old source names to new ones
    source_mapping = {
        "Garmin Garmin Connect": "Garmin Connect",
        "Map My Fitness MapMyRun iPhone": "MapMyRun iPhone",
        "Map My Fitness MapMyRun Android": "MapMyRun Android",
        "Map My Fitness MapMyRide Android": "MapMyRide Android",
        "Map My Fitness MapMyRide Android App": "MapMyRide Android"
    }

    try:
        logger.info("Starting cleanup of activity source names...")
        
        # Get all workouts to check
        all_workouts = session.query(Workout).all()
        
        updated_count = 0
        
        with tqdm(total=len(all_workouts), desc="Cleaning Source Names") as pbar:
            for workout in all_workouts:
                if workout.activity_name:
                    original_name = workout.activity_name
                    # Apply all replacements
                    for old_source, new_source in source_mapping.items():
                        if old_source in workout.activity_name:
                            workout.activity_name = workout.activity_name.replace(old_source, new_source)
                    
                    if original_name != workout.activity_name:
                        updated_count += 1
                pbar.update(1)

        if updated_count > 0:
            session.commit()
            logger.info(f"Successfully cleaned up source names for {updated_count} workouts.")
        else:
            logger.info("No activity names required cleanup.")

    except Exception as e:
        logger.error(f"An error occurred during source name cleanup: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    cleanup_sources() 