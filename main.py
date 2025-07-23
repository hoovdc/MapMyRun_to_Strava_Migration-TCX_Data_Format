import logging
import os
import time
from dotenv import load_dotenv
from tqdm import tqdm
import psutil
import argparse

from src.csv_parser import WorkoutInventory
from src.database_manager import DatabaseManager, Workout
from src.mmr_downloader import MmrDownloader
from src.strava_auth import StravaAuthenticator
from src.strava_uploader import StravaUploader
from src.tcx_validator import TcxValidator
from utils.logger import setup_logger


def main():
    """
    Main function to run the MapMyRun to Strava migration process.
    """
    parser = argparse.ArgumentParser(description="MapMyRun to Strava Migration Tool.")
    parser.add_argument('--dry-run', action='store_true', help="Simulate the upload process without making any actual API calls to Strava.")
    parser.add_argument('--csv-path', type=str, default='data/From_MapMyRun/CSV_for_event_ID_extraction/user16881_workout_history.csv', help='Path to the MapMyRun workout history CSV file.')
    args = parser.parse_args()

    load_dotenv(dotenv_path='config/.env')
    setup_logger()
    logger = logging.getLogger(__name__)
    
    if args.dry_run:
        logger.info("--- RUNNING IN DRY-RUN MODE ---")

    logger.info("Starting MapMyRun to Strava Migration.")

    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    try:
        # If the DB was just rebuilt, we must re-populate and re-validate everything.
        if db_manager.was_rebuilt:
            logger.info("Database was rebuilt. Repopulating from CSV and re-validating local TCX files.")
            
            # 1. Populate from CSV
            inventory = WorkoutInventory(args.csv_path)
            workouts_data = inventory.extract_workouts()
            
            if workouts_data:
                for workout_data in workouts_data:
                    workout = Workout(**workout_data)
                    session.add(workout)
                session.commit()
                logger.info(f"Successfully populated database with {len(workouts_data)} workouts.")
            else:
                logger.error("No workouts extracted from CSV. Halting.")
                return

            # 2. Re-validate all TCX files against the new DB records
            all_workouts = session.query(Workout).all()
            logger.info(f"--- Starting re-validation of {len(all_workouts)} workouts ---")
            validator = TcxValidator()
            validated_count = 0
            with tqdm(total=len(all_workouts), desc="Re-validating TCX files") as pbar:
                for workout in all_workouts:
                    tcx_file_name = f"{workout.workout_id}.tcx"
                    tcx_file_path = os.path.join('data', 'From_MapMyRun', 'TCX_downloads', tcx_file_name)
                    
                    if os.path.exists(tcx_file_path):
                        if validator.validate(tcx_file_path):
                            workout.mmr_status = 'validation_successful'
                            workout.download_path = tcx_file_path
                            validated_count += 1
                    pbar.update(1)
            session.commit()
            logger.info(f"Re-validation complete. Successfully validated {validated_count} existing TCX files.")


        # --- Download any remaining pending workouts (if any) ---
        pending_workouts = session.query(Workout).filter(Workout.mmr_status == 'pending_download').all()
        
        if not pending_workouts:
            logger.info("No pending workouts to download. All workouts are processed.")
        else:
            logger.info(f"Found {len(pending_workouts)} workouts with 'pending_download' status.")
            
            batch_size = 50  # Default batch size
            try:
                user_input = input(f"Enter batch size for downloading (Default: {batch_size}, enter 0 to skip): ").strip()
                if user_input:
                    batch_size = int(user_input)
            except ValueError:
                logger.warning(f"Invalid input. Using default batch size of {batch_size}.")

            if batch_size > 0:
                logger.info(f"--- Starting full download and validation with batch size of {batch_size} ---")
                cookie_string = os.getenv("MAPMYRUN_COOKIE_STRING")
                if not cookie_string or cookie_string == 'paste_your_full_cookie_string_here':
                    logger.error("MAPMYRUN_COOKIE_STRING is not set in config/.env.")
                    return
                    
                downloader = MmrDownloader(cookie_string=cookie_string)
                validator = TcxValidator()
                
                successful_downloads = 0
                failed_downloads = 0

                for i in range(0, len(pending_workouts), batch_size):
                    batch = pending_workouts[i:i + batch_size]
                    logger.info(f"Processing batch {i//batch_size + 1} of {len(pending_workouts)//batch_size + 1} ({len(batch)} workouts)")
                    
                    mem_percent = psutil.virtual_memory().percent
                    if mem_percent > 80:
                        logger.warning(f"High memory usage ({mem_percent}%). Pausing for 10 seconds.")
                        time.sleep(10)
                    
                    with tqdm(total=len(batch), desc=f"Batch {i//batch_size + 1}", leave=False) as pbar:
                        for workout in batch:
                            try:
                                with session.begin_nested():
                                    tcx_file_name = f"workout_{workout.workout_id}.tcx"
                                    tcx_file_path = os.path.join(downloader.output_dir, tcx_file_name)
                                    
                                    if os.path.exists(tcx_file_path):
                                        logger.debug(f"Existing file found for workout {workout.workout_id}. Validating.")
                                        if validator.validate(tcx_file_path):
                                            workout.mmr_status = 'validation_successful'
                                            workout.download_path = tcx_file_path
                                            successful_downloads += 1
                                            pbar.update(1)
                                            continue
                                    
                                    downloaded_path = downloader.download_tcx(workout.workout_id)
                                    
                                    if downloaded_path:
                                        if validator.validate(str(downloaded_path)):
                                            workout.mmr_status = 'validation_successful'
                                            workout.download_path = str(downloaded_path)
                                            successful_downloads += 1
                                        else:
                                            workout.mmr_status = 'validation_failed'
                                            failed_downloads += 1
                                    else:
                                        workout.mmr_status = 'download_failed'
                                        failed_downloads += 1
                            
                            except Exception as e:
                                logger.error(f"Error on workout {workout.workout_id}: {e}. Marked as 'download_failed'.")
                                workout.mmr_status = 'download_failed'
                                failed_downloads += 1
                                session.rollback()
                            
                            pbar.update(1)
                            time.sleep(2)
                    
                    session.commit()
                    logger.info(f"Batch complete. Pausing 5 seconds.")
                    time.sleep(5)
                
                logger.info(f"Full download and validation process complete. Successful: {successful_downloads}, Failed: {failed_downloads}.")
            else:
                logger.info("Skipping download process as requested.")
        
        # --- Phase 5: Strava Integration ---
        logger.info("--- Starting Strava Integration ---")
        strava_client_id = os.getenv("STRAVA_CLIENT_ID")
        strava_client_secret = os.getenv("STRAVA_CLIENT_SECRET")
        
        if not strava_client_id or not strava_client_secret:
            logger.error("Strava client ID and secret not found in config/.env.")
            return

        try:
            authenticator = StravaAuthenticator(client_id=strava_client_id, client_secret=strava_client_secret)
            strava_client = authenticator.authenticate()
            
            athlete = strava_client.get_athlete()
            logger.info(f"Successfully authenticated with Strava as: {athlete.firstname} {athlete.lastname}")

            # --- Phase 6: Strava Bulk Upload ---
            uploader = StravaUploader(client=strava_client, db_session=session, dry_run=args.dry_run)
            
            workouts_to_upload = session.query(Workout).filter(
                Workout.mmr_status == 'validation_successful',
                (Workout.strava_status == 'pending_upload') | (Workout.strava_status == 'upload_failed')
            ).all()

            if not workouts_to_upload:
                logger.info("No workouts pending for Strava upload.")
            else:
                logger.info(f"Found {len(workouts_to_upload)} workouts ready to upload to Strava.")
                
                if args.dry_run:
                    logger.info(f"[DRY-RUN] Simulating upload for {len(workouts_to_upload)} workouts.")
                    uploader.bulk_upload(workouts_to_upload)
                    logger.info("[DRY-RUN] Simulation complete. No data was sent to Strava.")
                    return

                print("\n--- Strava Upload Options ---")
                print("1. Upload a single activity for testing.")
                print("2. Bulk upload pending activities (select batch size)...")
                print("3. Cancel and exit.")
                
                try:
                    choice = input("Please select an option (1, 2, or 3): ").strip()

                    if choice == '1':
                        logger.info("Uploading the first pending workout as a test...")
                        test_workout = workouts_to_upload[0]
                        uploader.upload_activity(test_workout)
                        logger.info("Test upload complete. Please check the result on the Strava website.")
                    elif choice == '2':
                        batch_size_options = [5, 10, 50, 100, 300]
                        default_batch_size = 50

                        print(f"\nFound {len(workouts_to_upload)} workouts to upload.")
                        print("\n--- Select Batch Size ---")
                        print(f"Available options: {', '.join(map(str, batch_size_options))}")
                        
                        try:
                            user_input = input(f"Enter a batch size (Default: {default_batch_size}): ").strip()
                            batch_size = int(user_input) if user_input else default_batch_size
                            if batch_size not in batch_size_options:
                                logger.error("Invalid batch size selected. Aborting.")
                                return
                        except ValueError:
                            logger.error("Invalid input. Please enter a number. Aborting.")
                            return

                        # --- Interactive Batch Upload Loop ---
                        total_workouts = len(workouts_to_upload)
                        for i in range(0, total_workouts, batch_size):
                            batch = workouts_to_upload[i:i + batch_size]
                            num_remaining = total_workouts - (i + len(batch))
                            
                            logger.info(f"\n--- Preparing Batch {i//batch_size + 1} of {(total_workouts + batch_size - 1)//batch_size} ---")
                            logger.info(f"{len(batch)} workouts in this batch. {num_remaining} workouts remaining after this batch.")

                            uploader.bulk_upload(batch)

                            if num_remaining > 0:
                                print("\n--- Next Step ---")
                                print("1. Upload the next batch.")
                                print("2. Cancel and exit.")
                                
                                next_choice = input("Please select an option (1 or 2): ").strip()
                                if next_choice != '1':
                                    logger.info("User cancelled bulk upload. Exiting.")
                                    break
                        
                        logger.info("Bulk upload process finished.")

                    elif choice == '3':
                        logger.info("User cancelled. Exiting.")
                        
                except KeyboardInterrupt:
                    logger.info("\nStrava upload cancelled by user.")

        except Exception as e:
            logger.error(f"An error occurred during the Strava integration process: {e}")

    finally:
        if session:
            session.close()
            logger.info("Database session closed.")

    logger.info("Migration script finished.")


if __name__ == "__main__":
    main()
