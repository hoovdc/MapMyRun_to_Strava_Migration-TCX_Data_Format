import sys
import os
import logging
from sqlalchemy import func

# pylint: disable=not-callable
# SQLAlchemy func calls are dynamic and confuse static analyzers

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database_manager import DatabaseManager, Workout
from utils.logger import setup_logger
from utils.date_range_analyzer import DateRangeAnalyzer

def generate_status_report():
    """
    Connects to the database and generates a report of workout statuses.
    """
    setup_logger(level=logging.WARNING) # Keep console clean
    logger = logging.getLogger(__name__)

    db_manager = DatabaseManager()
    session = db_manager.get_session()

    try:
        logger.info("Generating database status report...")

        # --- MMR Status Report ---
        mmr_status_counts = session.query(
            Workout.mmr_status, func.count(Workout.mmr_status)
        ).group_by(Workout.mmr_status).all()
        
        print("\n--- MapMyRun Download/Validation Status ---")
        if not mmr_status_counts:
            print("No workouts found in the database.")
            return

        total_mmr_workouts = 0
        print(f"{'MMR Status':<25} | {'Count':<10}")
        print("-" * 38)
        for status, count in mmr_status_counts:
            print(f"{status:<25} | {count:<10}")
            total_mmr_workouts += count
        print("-" * 38)
        print(f"{'Total Workouts':<25} | {total_mmr_workouts:<10}\n")


        # --- Strava Status Report ---
        strava_status_counts = session.query(
            Workout.strava_status, func.count(Workout.strava_status)
        ).group_by(Workout.strava_status).all()

        print("--- Strava Upload Status ---")
        if not strava_status_counts:
            print("No workouts found with Strava status.")
            return
            
        total_strava_workouts = 0
        print(f"{'Strava Status':<25} | {'Count':<10}")
        print("-" * 38)
        for status, count in strava_status_counts:
            print(f"{status:<25} | {count:<10}")
            total_strava_workouts += count
        print("-" * 38)
        print(f"{'Total Workouts':<25} | {total_strava_workouts:<10}\n")
        
        # --- Date Range Analysis ---
        DateRangeAnalyzer(session, Workout).generate_analysis()

    except Exception as e:
        logger.error("An error occurred while generating the report: %s", e)
    finally:
        session.close()

if __name__ == "__main__":
    generate_status_report() 