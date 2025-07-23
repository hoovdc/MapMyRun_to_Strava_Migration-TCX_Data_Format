import sys
import os
import logging

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database_manager import DatabaseManager, Workout
from utils.logger import setup_logger

def get_failed_ids():
    """
    Connects to the database and retrieves the workout IDs of all workouts
    that have a status of 'validation_failed'.
    """
    setup_logger(level=logging.WARNING) # Keep console clean
    logger = logging.getLogger(__name__)

    db_manager = DatabaseManager()
    session = db_manager.get_session()

    try:
        logger.info("Fetching workout IDs for failed validations...")

        failed_workouts = session.query(Workout.workout_id).filter(
            Workout.mmr_status == 'validation_failed'
        ).all()
        
        if not failed_workouts:
            print("No workouts with status 'validation_failed' found.")
            return

        print("\n--- Workout IDs with 'validation_failed' status ---")
        # Extract the integer from the tuple result
        failed_ids = [result[0] for result in failed_workouts]
        for workout_id in failed_ids:
            print(workout_id)
        
        print(f"\nFound {len(failed_ids)} failed workouts.")
        print("You can find the corresponding TCX file in 'data/From_MapMyRun/TCX_downloads/'")
        print("For example, for ID 8633193603, the file is '8633193603.tcx'.")


    except Exception as e:
        logger.error(f"An error occurred while fetching failed workout IDs: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    get_failed_ids() 