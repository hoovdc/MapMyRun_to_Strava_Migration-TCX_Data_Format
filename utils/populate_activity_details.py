import sys
import os
import logging
import pandas as pd
from tqdm import tqdm

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database_manager import DatabaseManager, Workout
from src.csv_parser import WorkoutInventory # To use its _extract_id_from_link method
from utils.logger import setup_logger

def populate_details():
    """
    Connects to the database and populates the 'activity_name' and 'notes'
    fields for all workouts using data from the source CSV.
    """
    setup_logger(level=logging.INFO)
    logger = logging.getLogger(__name__)

    db_manager = DatabaseManager()
    session = db_manager.get_session()

    # Define the path to the CSV file
    csv_path = os.path.join(project_root, 'data', 'From_MapMyRun', 'CSV_for_event_ID_extraction', 'user16881_workout_history.csv')
    
    if not os.path.exists(csv_path):
        logger.error(f"Source CSV file not found at: {csv_path}")
        return

    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Successfully loaded {len(df)} records from CSV.")

        # Create a dictionary for quick lookup: {workout_id: workout_object}
        workouts_dict = {w.workout_id: w for w in session.query(Workout).all()}
        
        updated_count = 0
        parser_helper = WorkoutInventory(csv_path='') # Helper to extract IDs

        logger.info("Starting to populate activity names and notes...")
        with tqdm(total=len(df), desc="Populating Details") as pbar:
            for index, row in df.iterrows():
                workout_id = parser_helper._extract_id_from_link(row.get('Link', ''))
                if not workout_id:
                    pbar.update(1)
                    continue

                if workout_id in workouts_dict:
                    workout = workouts_dict[workout_id]
                    
                    # --- Generate the new, descriptive title ---
                    activity_type = row.get('Activity Type', 'Workout')
                    workout_date_obj = parser_helper._parse_date(row.get('Workout Date'))
                    workout_date_str = workout_date_obj.strftime('%Y-%m-%d') if workout_date_obj else ''
                    source = row.get('Source', '')
                    
                    # Format the title as requested
                    new_title = f"{activity_type} on {workout_date_str}"
                    if pd.notna(source) and source:
                        new_title += f" from {source}"

                    # Get notes
                    notes = row.get('Notes')
                    
                    # Update only if the data has changed
                    if workout.activity_name != new_title or workout.notes != notes:
                        workout.activity_name = new_title
                        workout.notes = notes if pd.notna(notes) else None
                        updated_count += 1
                
                pbar.update(1)

        if updated_count > 0:
            session.commit()
            logger.info(f"Successfully populated details for {updated_count} workouts.")
        else:
            logger.info("No workouts required an update. Details are already populated.")

    except Exception as e:
        logger.error(f"An error occurred while populating details: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    populate_details() 