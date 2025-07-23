import logging
import os
import time
from typing import List, Optional
from datetime import datetime, time as dt_time

from stravalib.client import Client
from stravalib.exc import ActivityUploadFailed, RateLimitExceeded
from sqlalchemy.orm.session import Session
from tcxreader.tcxreader import TCXReader
from tqdm import tqdm

from src.database_manager import Workout

logger = logging.getLogger(__name__)

class StravaUploader:
    """
    Handles uploading workout files to Strava.
    """
    def __init__(self, client: Client, db_session: Session, dry_run: bool = False):
        """
        Initializes the uploader with an authenticated stravalib client and a DB session.

        Args:
            client: An authenticated stravalib.Client instance.
            db_session: An active SQLAlchemy session.
            dry_run: If True, simulate uploads without making API calls.
        """
        self.client = client
        self.db_session = db_session
        self.dry_run = dry_run

    def _is_duplicate(self, workout: Workout) -> Optional[int]:
        """
        Checks Strava for activities on the same day with similar distance and duration.
        Returns the Strava activity ID of the duplicate if found, otherwise None.
        """
        try:
            # 1. Parse the local TCX file to get its metrics
            tcx = TCXReader().read(workout.download_path)
            local_distance = tcx.distance
            local_duration = tcx.duration
            
            if local_distance is None or local_duration is None:
                logger.warning(f"Could not parse distance/duration from TCX file for workout {workout.workout_id}. Skipping duplicate check.")
                return None

            # 2. Define the time range for the Strava query (the entire day)
            day_start = datetime.combine(workout.workout_date.date(), dt_time.min)
            day_end = datetime.combine(workout.workout_date.date(), dt_time.max)

            # 3. Query Strava for activities on that day
            remote_activities = self.client.get_activities(after=day_start, before=day_end)
            
            # 4. Compare metrics
            for activity in remote_activities:
                remote_distance = activity.distance.num
                remote_duration = activity.elapsed_time.total_seconds()
                
                # Use a tolerance for comparison (e.g. within 0.1 miles and 60 seconds)
                distance_diff = abs(local_distance - remote_distance)
                duration_diff = abs(local_duration - remote_duration)
                
                if distance_diff < 161 and duration_diff < 60:
                    logger.info(f"Found likely duplicate for workout {workout.workout_id}. Local: ({local_distance:.0f}m, {local_duration:.0f}s), Remote Strava ID {activity.id}: ({remote_distance:.0f}m, {remote_duration:.0f}s).")
                    return activity.id
            
            return None
            
        except RateLimitExceeded:
            self._handle_rate_limit()
            return self._is_duplicate(workout) # Retry after waiting
        except Exception as e:
            logger.error(f"An unexpected error occurred during duplicate check for workout {workout.workout_id}: {e}. Proceeding with upload attempt.")
            return None

    def _handle_rate_limit(self):
        """Pauses execution when a rate limit error is detected."""
        logger.warning("Strava API rate limit exceeded. Pausing for 15 minutes...")
        for i in tqdm(range(900), desc="Rate Limit Cooldown"):
            time.sleep(1)
        logger.info("Resuming...")

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

    def upload_activity(self, workout: Workout) -> None:
        """
        Uploads a single TCX file to Strava, including metadata from the database.
        """
        logger.info(f"Preparing to upload workout {workout.workout_id} ({workout.activity_name})...")
        
        if not workout.download_path or not os.path.exists(workout.download_path):
            logger.error(f"TCX file not found for workout {workout.workout_id} at {workout.download_path or '[No Path]'}")
            workout.strava_status = 'upload_failed_file_not_found'
            self.db_session.commit()
            return

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would upload '{workout.activity_name}' with external_id 'mmr_{workout.workout_id}'.")
            return

        # --- Proactive Duplicate Check ---
        if duplicate_id := self._is_duplicate(workout):
            workout.strava_status = 'skipped_already_exists'
            workout.strava_activity_id = duplicate_id
            self.db_session.commit()
            return

        # Pre-calculate the mapped activity type once
        mapped_activity_type = self._map_activity_type(workout.activity_type)

        try:
            # fallback name
            name = workout.activity_name or f"{mapped_activity_type.title()} on {workout.workout_date:%Y-%m-%d}"
            
            with open(workout.download_path, 'rb') as f:
                uploader = self.client.upload_activity(
                    activity_file=f,
                    data_type='tcx',
                    name=name,
                    description=f"Imported from MapMyRun.\nOriginal Notes: {workout.notes or ''}",
                    activity_type=mapped_activity_type,
                    external_id=f"mmr_{workout.workout_id}" # Helps prevent duplicates
                )
                
                if uploader is None:
                    # Stravalib returns None if the upload is immediately rejected.
                    raise ActivityUploadFailed("Upload immediately rejected by Strava. The TCX file may be corrupt or invalid.")

                # --- Manual Polling Loop with Timeout ---
                start_time = time.time()
                timeout = 300  # 5 minutes

                while uploader and uploader.is_processing:
                    if time.time() - start_time > timeout:
                        raise ActivityUploadFailed(f"Upload for workout {workout.workout_id} timed out after {timeout} seconds.")
                    
                    logger.debug(f"Polling for upload status of workout {workout.workout_id}...")
                    time.sleep(3)
                    uploader = uploader.poll()

                if uploader and uploader.is_complete:
                    activity = uploader.activity
                    workout.strava_status = 'upload_successful'
                    workout.strava_activity_id = activity.id
                    self.db_session.commit()
                    logger.info(f"Successfully uploaded workout {workout.workout_id}. Strava Activity ID: {activity.id}")
                elif uploader and uploader.is_error:
                    # Raise an exception to be caught by our existing handler
                    raise ActivityUploadFailed(f"Upload failed with error: {uploader.error}")
                else:
                    # This handles timeout or poll() returning None
                    raise ActivityUploadFailed(f"Upload finished in an unknown state or was rejected mid-process. Uploader is {uploader}.")

        except ActivityUploadFailed as e:
            resp = getattr(e, "response", None)
            
            # Check for rate limit response first
            if resp and resp.status_code == 429:
                self._handle_rate_limit()
                self.upload_activity(workout) # Retry the upload after waiting
                return 

            # Safely check for a response and a 409 status code for duplicates
            if resp and resp.status_code == 409:
                logger.warning(f"Upload failed for workout {workout.workout_id}: It already exists on Strava (409 Conflict).")
                workout.strava_status = 'skipped_already_exists'
            else:
                # Handle other upload errors where a response might not exist
                error_details = str(e)
                logger.error(f"Upload failed for workout {workout.workout_id}: {error_details}")
                
                # Check for the duplicate string as a fallback for older stravalib versions or different error types
                if 'duplicate of' in error_details.lower():
                     workout.strava_status = 'skipped_already_exists'
                else:
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


    def bulk_upload(self, workouts: List[Workout]) -> None:
        """
        Uploads a single batch of workouts to Strava. The calling function
        is responsible for iteration and delays.

        Args:
            workouts: A list of Workout objects (a single batch) to be uploaded.
        """
        logger.info(f"Processing batch of {len(workouts)} workouts...")
        
        with tqdm(total=len(workouts), desc="Uploading Batch") as pbar:
            for workout in workouts:
                self.upload_activity(workout)
                pbar.update(1)
                # Safer per-upload delay to keep under Strava's 100 uploads / 15 min cap
                time.sleep(6)

        logger.info("Batch complete.")
