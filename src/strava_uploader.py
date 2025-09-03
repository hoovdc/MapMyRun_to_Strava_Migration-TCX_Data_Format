import logging
import os
import time
from typing import List, Optional
from datetime import datetime, time as dt_time, timedelta

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
        self.api_call_count = 0
        self.api_call_start_time = time.time()

    def _count_api_call(self, operation_name: str):
        """Track API calls for rate limit monitoring"""
        self.api_call_count += 1
        elapsed = time.time() - self.api_call_start_time
        logger.debug(f"API call #{self.api_call_count} ({operation_name}) - {elapsed:.1f}s elapsed")
        
        # Strava limits: 200 overall/15min, 100 non-upload/15min
        upload_operations = {'upload_activity', 'poll_upload'}
        if operation_name in upload_operations:
            limit = 200  # Overall limit includes uploads
            warning_threshold = 160  # 80% of overall limit
        else:
            limit = 100  # Non-upload limit (get_activities, etc.)
            warning_threshold = 80   # 80% of non-upload limit
            
        if self.api_call_count % 20 == 0:
            logger.info(f"API usage: {self.api_call_count} calls in {elapsed/60:.1f} minutes")
            if self.api_call_count >= warning_threshold:
                logger.warning(f"Approaching rate limit ({self.api_call_count}/{limit} in 15min window)")

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
            self._count_api_call("get_activities")
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
            
        except RateLimitExceeded as e:
            logger.error(f"Rate limit exceeded (dedicated exception): {e}")
            self._handle_rate_limit()
            return self._is_duplicate(workout)  # Retry after waiting
        except Exception as e:
            # Enhanced diagnostic logging
            logger.error(f"Exception in _is_duplicate for workout {workout.workout_id}: "
                        f"Type: {type(e).__name__}, Message: {str(e)}")
            
            # Fallback logic for status code checking
            response = getattr(e, 'response', None)
            if response and hasattr(response, 'status_code') and response.status_code == 429:
                headers = getattr(response, 'headers', None)
                if headers:
                    logger.debug(f"Rate limit headers: {dict(headers)}")
                self._handle_rate_limit(headers)
                return self._is_duplicate(workout)
            
            logger.error(f"An unexpected error occurred during duplicate check for workout {workout.workout_id}: {e}. Proceeding with upload attempt.")
            return None

    def _handle_rate_limit(self, headers=None):
        """Pauses execution when a rate limit error is detected."""
        # Calculate time until next 15-minute reset interval (0, 15, 30, 45 minutes after hour)
        from datetime import datetime, timedelta
        now = datetime.now()
        minutes_past_hour = now.minute
        
        # Find next reset point
        next_reset_minute = ((minutes_past_hour // 15) + 1) * 15
        if next_reset_minute >= 60:
            next_reset_minute = 0
            next_reset_hour = (now.hour + 1) % 24
        else:
            next_reset_hour = now.hour
        
        next_reset = now.replace(hour=next_reset_hour, minute=next_reset_minute, second=0, microsecond=0)
        if next_reset <= now:
            next_reset += timedelta(days=1)
        
        # Default: wait until next reset + 30s buffer
        default_cooldown = int((next_reset - now).total_seconds()) + 30
        
        # Use Retry-After if provided and reasonable
        cooldown = default_cooldown
        if headers and 'Retry-After' in headers:
            try:
                retry_after = int(headers['Retry-After'])
                if 0 < retry_after <= 900:  # Sanity check
                    cooldown = retry_after
                    logger.info(f"Using Retry-After header: {cooldown} seconds")
            except (ValueError, TypeError):
                logger.warning("Could not parse Retry-After header, using calculated cooldown")
        
        logger.warning(f"Strava API rate limit exceeded. Pausing for {cooldown // 60}m {cooldown % 60}s until next reset...")
        for i in tqdm(range(cooldown), desc="Rate Limit Cooldown"):
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
        log_fn = logger.debug if self.dry_run else logger.info
        log_fn(f"Preparing to upload workout {workout.workout_id} ({workout.activity_name})...")
        
        if not workout.download_path or not os.path.exists(workout.download_path):
            logger.error(f"TCX file not found for workout {workout.workout_id} at {workout.download_path or '[No Path]'}")
            workout.strava_status = 'upload_failed_file_not_found'
            self.db_session.commit()
            return

        if self.dry_run:
            log_fn(f"[DRY-RUN] Would upload '{workout.activity_name}' with external_id 'mmr_{workout.workout_id}'.")
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
                self._count_api_call("upload_activity")
                uploader = self.client.upload_activity(
                    activity_file=f,
                    data_type='tcx',
                    name=name,
                    description=f"Imported from MapMyRun.\nOriginal Notes: {workout.notes or ''}",
                    activity_type=mapped_activity_type,
                    external_id=f"mmr_{workout.workout_id}" # Helps prevent duplicates
                )
                
                if uploader is None:
                    # Comprehensive diagnostic logging (file-only)
                    error_msg = (
                        f"Upload immediately rejected by Strava for workout {workout.workout_id}. "
                        f"TCX file: {workout.download_path}"
                    )
                    logger.error(error_msg)

                    # File diagnostics
                    if workout.download_path and os.path.exists(workout.download_path):
                        file_size = os.path.getsize(workout.download_path)
                        logger.debug(f"TCX file exists, size: {file_size} bytes")

                        # Use existing TcxValidator class for validation diagnostics
                        from src.tcx_validator import TcxValidator
                        validator = TcxValidator()
                        is_valid = validator.validate(workout.download_path)
                        logger.debug(f"TCX validation result: {'PASSED' if is_valid else 'FAILED'}")
                    else:
                        logger.error("TCX file does not exist at specified path")

                    raise ActivityUploadFailed(
                        f"{error_msg}. Possible causes: corrupt file, invalid data, or API rejection."
                    )

                # --- Manual Polling Loop with Timeout ---
                start_time = time.time()
                timeout = 300  # 5 minutes

                while uploader and uploader.is_processing:
                    if time.time() - start_time > timeout:
                        raise ActivityUploadFailed(f"Upload for workout {workout.workout_id} timed out after {timeout} seconds.")
                    
                    logger.debug(f"Polling for upload status of workout {workout.workout_id}...")
                    time.sleep(3)
                    self._count_api_call("poll_upload")
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

        except FileNotFoundError:
            logger.error(f"TCX file not found for workout {workout.workout_id} at {workout.download_path}")
            workout.strava_status = 'upload_failed_file_not_found'
            self.db_session.commit()
        except RateLimitExceeded as e:
            logger.error(f"Rate limit exceeded (dedicated exception): {e}")
            self._handle_rate_limit()
            self.upload_activity(workout)  # Retry after waiting
            return
        except Exception as e:
            # Enhanced diagnostic logging
            logger.error(f"Exception in upload_activity for workout {workout.workout_id}: "
                        f"Type: {type(e).__name__}, Message: {str(e)}")
            
            response = getattr(e, 'response', None)
            if response and hasattr(response, 'status_code') and response.status_code == 429:
                headers = getattr(response, 'headers', None)
                if headers:
                    logger.debug(f"Rate limit headers: {dict(headers)}")
                self._handle_rate_limit(headers)
                self.upload_activity(workout)
                return

            if isinstance(e, ActivityUploadFailed):
                error_details = str(e).lower()
                if any(term in error_details for term in ['duplicate of', 'already exists', 'duplicate']):
                    logger.info(f"Detected duplicate for workout {workout.workout_id}: {e}. Skipping.")
                    workout.strava_status = 'skipped_already_exists'
                elif any(term in error_details for term in ['rate limit', 'exceeded', 'too many requests']):
                    logger.warning(f"Rate limit hit during upload for workout {workout.workout_id}: {e}. Retrying after cooldown.")
                    self._handle_rate_limit(headers=getattr(response, 'headers', None))
                    self.upload_activity(workout)  # Immediate retry
                    return
                else:
                    logger.error(f"True upload failure for workout {workout.workout_id}: {e}")
                    workout.strava_status = 'upload_failed'
                self.db_session.commit()
                return

            # Fallback for any other unexpected exceptions
            logger.error(f"An unexpected error occurred during upload for workout {workout.workout_id}: {e}")
            workout.strava_status = 'upload_failed'
            self.db_session.rollback() # Rollback for unexpected errors
            self.db_session.commit()


    def bulk_upload(self, workouts: List[Workout]) -> None:
        """
        Uploads a single batch of workouts to Strava. The calling function
        is responsible for iteration and delays.

        Args:
            workouts: A list of Workout objects (a single batch) to be uploaded.
        """
        logger.info(f"Processing batch of {len(workouts)} workouts...")
        
        with tqdm(total=len(workouts), desc="Uploading Batch") as pbar:
            attempted_workouts: List[Workout] = []
            for workout in workouts:
                # Reduce console noise during dry-run by lowering per-item log verbosity
                if self.dry_run:
                    # Temporarily adjust logger level for this module to reduce INFO noise
                    module_logger = logging.getLogger(__name__)
                    previous_level = module_logger.level
                    try:
                        if previous_level <= logging.INFO:
                            module_logger.setLevel(logging.DEBUG)
                        self.upload_activity(workout)
                    finally:
                        module_logger.setLevel(previous_level)
                else:
                    self.upload_activity(workout)
                attempted_workouts.append(workout)
                pbar.update(1)
                # Safer per-upload delay to keep under Strava's 100 uploads / 15 min cap
                if not self.dry_run:
                    time.sleep(6)

        # --- Batch Summary ---
        if self.dry_run:
            logger.info(f"Batch complete. [DRY-RUN] Attempted: {len(attempted_workouts)} (no status changes in dry-run)")
        else:
            status_counts: dict[str, int] = {}
            for w in attempted_workouts:
                status_counts[w.strava_status] = status_counts.get(w.strava_status, 0) + 1
            
            true_failures = status_counts.get('upload_failed', 0) + status_counts.get('upload_failed_file_not_found', 0)
            skips = status_counts.get('skipped_already_exists', 0)
            successes = status_counts.get('upload_successful', 0)
            summary_text = f"success={successes}, skips={skips}, true_failures={true_failures}"
            
            logger.info(f"Batch complete. Attempted: {len(attempted_workouts)} | {summary_text}")
