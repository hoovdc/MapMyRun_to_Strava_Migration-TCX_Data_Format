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
    parser.add_argument('--dry-run-limit', type=int, default=20, help="Limit the number of activities simulated during dry-run (default: 20)")
    parser.add_argument('--csv-path', type=str, default='data/From_MapMyRun/CSV_for_event_ID_extraction/user16881_workout_history.csv', help='Path to the MapMyRun workout history CSV file.')
    parser.add_argument('--skip-non-runs', action='store_true', default=True, help="Skip non-run activities during upload (default: True - focus on runs first)")
    parser.add_argument('--include-all-types', dest='skip_non_runs', action='store_false', help="Include all activity types during upload")
    parser.add_argument('--batch-size', type=int, help="Run in non-interactive mode with specified batch size (5, 10, 50, 100, 300)")
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

            # Prioritize pending uploads, then randomized failed uploads to avoid
            # retrying the same records first on every run (no DB changes required).
            pending_to_upload = session.query(Workout).filter(
                Workout.mmr_status == 'validation_successful',
                Workout.strava_status == 'pending_upload'
            ).all()

            failed_to_retry = session.query(Workout).filter(
                Workout.mmr_status == 'validation_successful',
                Workout.strava_status == 'upload_failed'
            ).all()

            # Randomize failed set order for fair retries across runs
            import random as _random
            _random.shuffle(failed_to_retry)

            workouts_to_upload = pending_to_upload + failed_to_retry

            if not workouts_to_upload:
                logger.info("No workouts pending for Strava upload.")
            else:
                logger.info(
                    f"Found {len(workouts_to_upload)} workouts ready to upload to Strava "
                    f"({len(pending_to_upload)} pending + {len(failed_to_retry)} failed)."
                )
                
                # Apply activity type filtering before dry-run or actual upload
                if args.skip_non_runs:
                    workouts_to_upload = [w for w in workouts_to_upload if 'run' in w.activity_type.lower()]
                    logger.info(f"Filtered to {len(workouts_to_upload)} run activities (skipped non-runs).")
                
                if args.dry_run:
                    # Limit simulation size to keep console output concise
                    total = len(workouts_to_upload)
                    limit = max(0, args.dry_run_limit or 0)
                    limited_list = workouts_to_upload[:limit] if limit else workouts_to_upload
                    logger.info(f"[DRY-RUN] Simulating upload for {len(limited_list)} of {total} workouts (limit={limit}).")
                    uploader.bulk_upload(limited_list)
                    logger.info("[DRY-RUN] Simulation complete. No data was sent to Strava.")
                    return

                # Non-interactive mode with --batch-size
                if args.batch_size:
                    if args.batch_size not in [5, 10, 50, 100, 300]:
                        logger.error(f"Invalid batch size {args.batch_size}. Must be one of: 5, 10, 50, 100, 300")
                        return
                    
                    logger.info(f"Running in non-interactive mode with batch size {args.batch_size}")
                    batch = workouts_to_upload[:args.batch_size]
                    logger.info(f"Processing {len(batch)} workouts from {len(workouts_to_upload)} total")
                    uploader.bulk_upload(batch)
                    logger.info("Non-interactive upload complete.")
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
            # Generate final status summary
            print_final_status_summary(session)
            session.close()
            logger.info("Database session closed.")

    logger.info("Migration script finished.")


def print_final_status_summary(session):
    """
    Print a comprehensive summary of all workout statuses at the end of the run.
    """
    print("\n" + "="*60)
    print("FINAL STATUS SUMMARY")
    print("="*60)
    
    # Get all workouts
    all_workouts = session.query(Workout).all()
    total_workouts = len(all_workouts)
    
    if total_workouts == 0:
        print("No workouts found in database.")
        return
    
    # Count by MMR status
    mmr_status_counts = {}
    for workout in all_workouts:
        status = workout.mmr_status or 'unknown'
        mmr_status_counts[status] = mmr_status_counts.get(status, 0) + 1
    
    # Count by Strava status
    strava_status_counts = {}
    for workout in all_workouts:
        status = workout.strava_status or 'not_processed'
        strava_status_counts[status] = strava_status_counts.get(status, 0) + 1
    
    # Count by activity type
    activity_type_counts = {}
    for workout in all_workouts:
        activity_type = workout.activity_type or 'unknown'
        activity_type_counts[activity_type] = activity_type_counts.get(activity_type, 0) + 1
    
    # Display summary
    print(f"Total Workouts: {total_workouts}")
    print()
    
    print("MapMyRun Processing Status:")
    for status, count in sorted(mmr_status_counts.items()):
        percentage = (count / total_workouts) * 100
        print(f"  {status}: {count} ({percentage:.1f}%)")
    print()
    
    print("Strava Upload Status:")
    for status, count in sorted(strava_status_counts.items()):
        percentage = (count / total_workouts) * 100
        print(f"  {status}: {count} ({percentage:.1f}%)")
    print()
    
    print("Activity Types:")
    for activity_type, count in sorted(activity_type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_workouts) * 100
        print(f"  {activity_type}: {count} ({percentage:.1f}%)")
    print()
    
    # Calculate key metrics
    successful_uploads = strava_status_counts.get('upload_successful', 0)
    skipped_duplicates = strava_status_counts.get('skipped_already_exists', 0)
    confirmed_on_strava = successful_uploads + skipped_duplicates
    
    pending_uploads = strava_status_counts.get('pending_upload', 0)
    failed_uploads = strava_status_counts.get('upload_failed', 0)
    remaining_to_process = pending_uploads + failed_uploads
    
    print("KEY METRICS:")
    print(f"  Activities confirmed on Strava: {confirmed_on_strava} ({(confirmed_on_strava/total_workouts)*100:.1f}%)")
    print(f"  Activities remaining to process: {remaining_to_process} ({(remaining_to_process/total_workouts)*100:.1f}%)")
    
    # RUN-SPECIFIC METRICS (Priority Focus)
    run_workouts = [w for w in all_workouts if w.activity_type and 'run' in w.activity_type.lower()]
    total_runs = len(run_workouts)
    if total_runs > 0:
        run_confirmed = len([w for w in run_workouts if w.strava_status in ['upload_successful', 'skipped_already_exists']])
        run_pending = len([w for w in run_workouts if w.strava_status == 'pending_upload'])
        run_failed = len([w for w in run_workouts if w.strava_status == 'upload_failed'])
        
        print()
        print("RUN MIGRATION PROGRESS (Priority Focus):")
        print(f"  Total Runs: {total_runs} ({(total_runs/total_workouts)*100:.1f}% of all activities)")
        print(f"  Runs confirmed on Strava: {run_confirmed} ({(run_confirmed/total_runs)*100:.1f}%)")
        print(f"  Runs pending upload: {run_pending}")
        print(f"  Runs failed upload: {run_failed}")
        
        if run_confirmed / total_runs >= 0.95:
            print("  SUCCESS: 95%+ of runs are confirmed on Strava!")
        elif run_confirmed / total_runs >= 0.90:
            print("  EXCELLENT: 90%+ of runs are confirmed on Strava!")
        elif run_confirmed / total_runs >= 0.80:
            print("  GOOD: 80%+ of runs are confirmed on Strava!")
        else:
            print(f"  IN PROGRESS: {int(0.95 * total_runs) - run_confirmed} more run confirmations needed for 95% target")
    
    # Overall progress
    if confirmed_on_strava / total_workouts >= 0.95:
        print("  OVERALL SUCCESS: 95%+ of all activities are confirmed on Strava!")
    elif confirmed_on_strava / total_workouts >= 0.90:
        print("  OVERALL EXCELLENT: 90%+ of all activities are confirmed on Strava!")
    elif confirmed_on_strava / total_workouts >= 0.80:
        print("  OVERALL GOOD: 80%+ of all activities are confirmed on Strava!")
    else:
        print(f"  OVERALL IN PROGRESS: {int(0.95 * total_workouts) - confirmed_on_strava} more confirmations needed for 95% target")
    
    print("="*60)


if __name__ == "__main__":
    main()
