import logging
import os
import sys

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database_manager import DatabaseManager, Workout
from utils.logger import setup_logger

def _map_activity_type(mmr_type: str) -> str:
    """Maps MapMyRun activity types to supported Strava activity types."""
    if not mmr_type:
        return 'workout'
    
    mmr_type = mmr_type.lower()
    
    type_mapping = {
        'run': 'run', 'treadmill run': 'run', 'track run': 'run',
        'walk': 'walk', 'hike': 'hike',
        'bike': 'ride', 'biking': 'ride', 'cycle': 'ride', 'spin': 'ride',
        'swim': 'swim', 'elliptical': 'elliptical',
        'stairs': 'stairstepper', 'weight training': 'weighttraining'
    }
    
    for key, value in type_mapping.items():
        if key in mmr_type:
            return value
    
    return 'workout'

def normalize_activity_types():
    """
    Connects to the database and normalizes the activity_type for all workouts
    to conform to Strava's recognized types.
    """
    setup_logger()
    logger = logging.getLogger(__name__)
    
    logger.info("--- Starting Activity Type Normalization Utility ---")
    
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    try:
        workouts = session.query(Workout).all()
        if not workouts:
            logger.info("No workouts found in the database. Nothing to do.")
            return

        updated_count = 0
        for workout in workouts:
            original_type = workout.activity_type
            normalized_type = _map_activity_type(original_type)
            
            if original_type != normalized_type:
                workout.activity_type = normalized_type
                updated_count += 1
                logger.debug(f"Mapped '{original_type}' to '{normalized_type}' for workout {workout.workout_id}")

        if updated_count > 0:
            session.commit()
            logger.info(f"Successfully normalized the activity type for {updated_count} workout(s).")
        else:
            logger.info("All activity types are already normalized. No changes made.")

    except Exception as e:
        logger.error(f"An error occurred during activity type normalization: {e}")
        session.rollback()
    finally:
        session.close()
        logger.info("--- Activity Type Normalization Finished ---")

if __name__ == "__main__":
    normalize_activity_types() 