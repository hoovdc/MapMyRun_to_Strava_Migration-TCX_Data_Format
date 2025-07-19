import logging
import os
import sys

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database_manager import DatabaseManager, Workout
from src.csv_parser import WorkoutInventory
from utils.logger import setup_logger

def update_workout_metadata():
    """
    Connects to the existing database and updates each workout with the
    'activity_name' and 'notes' from the CSV file.
    """
    setup_logger()
    logger = logging.getLogger(__name__)
    
    logger.info("--- Starting Workout Metadata Update Utility ---")
    
    # 1. Load the workout data from the CSV
    csv_path = 'data/From_MapMyRun/CSV_for_event_ID_extraction/user16881_workout_history.csv'
    inventory = WorkoutInventory(csv_path)
    workouts_from_csv = {w['workout_id']: w for w in inventory.extract_workouts()}
    
    if not workouts_from_csv:
        logger.error("Could not load any workouts from the CSV. Halting.")
        return

    # 2. Connect to the database
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    try:
        workouts_in_db = session.query(Workout).all()
        
        if not workouts_in_db:
            logger.info("No workouts found in the database. Nothing to do.")
            return

        updated_count = 0
        for workout_db in workouts_in_db:
            csv_data = workouts_from_csv.get(workout_db.workout_id)
            if csv_data:
                # Check if an update is needed
                if (workout_db.activity_name != csv_data['activity_name'] or 
                    workout_db.notes != csv_data['notes']):
                    
                    workout_db.activity_name = csv_data['activity_name']
                    workout_db.notes = csv_data['notes']
                    updated_count += 1
            else:
                logger.warning(f"Workout ID {workout_db.workout_id} from DB not found in CSV. Skipping.")
        
        if updated_count > 0:
            session.commit()
            logger.info(f"Successfully updated metadata for {updated_count} workout(s).")
        else:
            logger.info("All workout metadata is already up-to-date. No changes made.")

    except Exception as e:
        logger.error(f"An error occurred during metadata update: {e}")
        session.rollback()
    finally:
        session.close()
        logger.info("--- Workout Metadata Update Finished ---")

if __name__ == "__main__":
    update_workout_metadata() 