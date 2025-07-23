import sys
import os
import logging
import argparse
from tqdm import tqdm

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database_manager import DatabaseManager, Workout
from src.tcx_validator import TcxValidator
from utils.logger import setup_logger

def revalidate_workouts(limit: int = None):
    """
    Connects to the database and re-runs validation on all workouts
    currently marked as 'validation_failed'.

    Args:
        limit: An optional integer to limit the number of workouts to process.
    """
    setup_logger(level=logging.INFO)
    logger = logging.getLogger(__name__)

    db_manager = DatabaseManager()
    session = db_manager.get_session()
    validator = TcxValidator()
    
    updated_count = 0
    still_failing_count = 0

    try:
        logger.info("Querying for workouts that previously failed validation...")
        
        workouts_to_revalidate = session.query(Workout).filter(
            Workout.mmr_status == 'validation_failed'
        )
        
        if limit:
            workouts_to_revalidate = workouts_to_revalidate.limit(limit)
        
        workouts_to_revalidate = workouts_to_revalidate.all()

        if not workouts_to_revalidate:
            logger.info("No workouts with status 'validation_failed' found to re-validate.")
            return

        logger.info(f"Found {len(workouts_to_revalidate)} workouts to re-validate. Starting process...")

        # Define the base directory for TCX files
        tcx_base_dir = os.path.join(project_root, 'data', 'From_MapMyRun', 'TCX_downloads')

        with tqdm(total=len(workouts_to_revalidate), desc="Re-validating workouts") as pbar:
            for workout in workouts_to_revalidate:
                # Manually construct the path instead of relying on the database
                expected_path = os.path.join(tcx_base_dir, f"{workout.workout_id}.tcx")

                if not os.path.exists(expected_path):
                    logger.warning(f"Skipping workout {workout.workout_id}: TCX file not found at {expected_path}.")
                    still_failing_count += 1
                    pbar.update(1)
                    continue

                if validator.validate(expected_path):
                    workout.mmr_status = 'validation_successful'
                    workout.download_path = expected_path # IMPORTANT: Populate the missing path
                    updated_count += 1
                else:
                    # If it still fails, we log it but don't change the status
                    logger.error(f"Workout {workout.workout_id} still fails validation with the new logic.")
                    still_failing_count += 1
                
                pbar.update(1)

        session.commit()
        logger.info("Re-validation process complete.")
        logger.info(f"Successfully updated {updated_count} workouts to 'validation_successful'.")
        logger.info(f"{still_failing_count} workouts are still failing validation.")

    except Exception as e:
        logger.error(f"An error occurred during re-validation: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-validate workouts that previously failed.")
    parser.add_argument('--limit', type=int, help="Limit the number of workouts to process.")
    args = parser.parse_args()

    revalidate_workouts(limit=args.limit) 