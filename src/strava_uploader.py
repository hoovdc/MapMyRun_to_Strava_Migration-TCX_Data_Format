import logging
import time
from typing import List

from stravalib.client import Client
from stravalib.exc import ActivityUploadFailed
from sqlalchemy.orm.session import Session

from src.database_manager import Workout

logger = logging.getLogger(__name__)

class StravaUploader:
    """
    Handles uploading workout files to Strava.
    """
    def __init__(self, client: Client, db_session: Session):
        """
        Initializes the uploader with an authenticated stravalib client and a DB session.

        Args:
            client: An authenticated stravalib.Client instance.
            db_session: An active SQLAlchemy session.
        """
        self.client = client
        self.db_session = db_session

    def _map_activity_type(self, mmr_type: str) -> str:
        """Maps MapMyRun activity types to supported Strava activity types."""
        if not mmr_type:
            return 'workout' # Default if no type is provided
        
        mmr_type = mmr_type.lower()
        
        # Mapping dictionary
        type_mapping = {
            'run': 'run',
            'treadmill run': 'run',
            'walk': 'walk',
            'hike': 'hike',
            'bike': 'ride',
            'biking': 'ride',
            'cycle': 'ride',
            'spin': 'ride',
            'swim': 'swim',
            'elliptical': 'elliptical',
            'stairs': 'stairstepper',
            'weight training': 'weighttraining'
        }
        
        for key, value in type_mapping.items():
            if key in mmr_type:
                return value
        
        return 'workout' # Fallback for any unmapped types

    def upload_activity(self, workout: Workout):
        """
        Uploads a single TCX file to Strava, including metadata from the database.
        """
        # Generate a sensible default name if the activity name is missing
        activity_name = workout.activity_name
        if not activity_name or activity_name.strip() == '':
            activity_name = f"{workout.activity_type.replace('_', ' ').title()} on {workout.workout_date.strftime('%Y-%m-%d')}"
        
        logger.info(f"Uploading workout {workout.workout_id} ({activity_name}) to Strava...")
        
        strava_activity_type = self._map_activity_type(workout.activity_type)
        
        try:
            with open(workout.download_path, 'rb') as f:
                uploader = self.client.upload_activity(
                    activity_file=f,
                    data_type='tcx',
                    name=activity_name,
                    description=f"Imported from MapMyRun.\nOriginal Notes: {workout.notes or ''}",
                    external_id=f"mmr_{workout.workout_id}" # Helps prevent duplicates
                )
                
                # Wait for the upload to be processed by Strava
                activity = uploader.wait()
                
                workout.strava_status = 'upload_successful'
                workout.strava_activity_id = activity.id
                self.db_session.commit()
                logger.info(f"Successfully uploaded workout {workout.workout_id}. Strava Activity ID: {activity.id}")

        except ActivityUploadFailed as e:
            error_details = str(e)
            
            # This is the most reliable way to check for the duplicate error string.
            if 'duplicate of' in error_details.lower():
                logger.warning(f"Skipping workout {workout.workout_id}: It already exists on Strava.")
                workout.strava_status = 'skipped_already_exists'
                self.db_session.commit()
            else:
                logger.error(f"Upload failed for workout {workout.workout_id}: {error_details}")
                workout.strava_status = 'upload_failed'
                self.db_session.commit()
        except FileNotFoundError:
            logger.error(f"TCX file not found for workout {workout.workout_id} at {workout.download_path}")
            workout.strava_status = 'upload_failed_file_not_found'
            self.db_session.commit()
        except Exception as e:
            logger.error(f"An unexpected error occurred during upload for workout {workout.workout_id}: {e}")
            workout.strava_status = 'upload_failed'
            self.db_session.rollback() # Rollback for unexpected errors


    def bulk_upload(self, workouts: List[Workout], batch_size: int = 5, delay: int = 30):
        """
        Uploads a list of workouts to Strava in managed batches with delays.

        Args:
            workouts: A list of Workout objects to be uploaded.
            batch_size: The number of workouts to upload in each batch.
            delay: The number of seconds to wait between batches to respect rate limits.
        """
        num_workouts = len(workouts)
        logger.info(f"Starting bulk upload of {num_workouts} workouts to Strava.")
        
        for i in range(0, num_workouts, batch_size):
            batch = workouts[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {num_workouts//batch_size + 1} ({len(batch)} workouts)")
            
            for workout in batch:
                self.upload_activity(workout)
                time.sleep(2) # Small delay between individual uploads
            
            if i + batch_size < num_workouts:
                logger.info(f"Batch complete. Pausing for {delay} seconds before next batch.")
                time.sleep(delay)

        logger.info("Bulk upload process complete.") 