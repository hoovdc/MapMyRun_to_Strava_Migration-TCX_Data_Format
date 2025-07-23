# MapMyRun to Strava Migration Development Plan

## Project Overview

This development plan outlines a phased approach to migrate fitness data from MapMyRun to Strava using Python automation. The project will extract workout data from MapMyRun, download detailed TCX files, and facilitate bulk upload to Strava.

## Project Clarifications
- I have about 600 workouts to sync.
- I plan to do this only once. In other words, I don't plan to do additional bulk transfers of this data in the future. I'll just use Strava to capture the data in the future.
- I don't want to use the MapMyRun API right now because I believe it would require a delay in my project for human approval of the granting of my API key.
- I am the only user of this project.
- **Strategy Pivot**: The initial plan to use Selenium for UI automation proved too brittle and unreliable due to anti-bot measures on MapMyRun's website. The project has pivoted to a more robust strategy using direct `requests` calls authenticated via a manually extracted session cookie. This bypasses the UI entirely.

## Phase 0: Prerequisites & Setup (2-3 hours)

### Objectives
- Set up development environment
- Obtain necessary credentials and authentication tokens
- Validate access to both platforms

Note: The initial attempt to use public visibility for unauthenticated downloads failed. The subsequent attempt to use Selenium for authenticated downloads also failed due to website complexity. The plan is now updated to use a robust, cookie-based authentication method.

### Tasks
1. **Development Environment Setup**
   - [x] Install Python 3.8+ 
   - [x] Create virtual environment: `python -m venv .venv`
   - [x] Install required packages:
     ```bash
     pip install pandas requests stravalib python-dotenv beautifulsoup4 tcxreader
     ```
   - [x] Install Chrome browser (if not present, for manual cookie extraction)

2. **Credential Preparation**
   - [x] MapMyRun Credentials: Instead of username/password, use a session cookie.
     - [x] Follow the guide at [docs/how-to-download-tcx.md](docs/how-to-download-tcx.md) to get the required cookie string.
   - [x] Create Strava API application at https://www.strava.com/settings/api
   - [x] Note Client ID, Client Secret from Strava
   - [x] Set Authorization Callback Domain to `localhost`
   - [x] Create `config/.env` file
   - [x] Populate `.env` with credential values:
     ```
     # In config/.env
     MAPMYRUN_COOKIE_STRING='paste_your_full_cookie_string_here'
     STRAVA_CLIENT_ID=your_id
     STRAVA_CLIENT_SECRET=your_secret
     ```

   Note: This cookie-based method is far more reliable than UI automation and does not require making workouts public.

3. **Data Export from MapMyRun**
   - [x] Log into MapMyRun web interface
   - [x] Export workout history CSV from https://www.mapmyfitness.com/workout/export/csv
   - [x] Save as `data/From_MapMyRun/CSV_for_event_ID_extraction/mapmyrun_export.csv` in project directory
   - [x] The path to this CSV can be overridden with the `--csv-path` command-line argument.
   - [x] Verify CSV contains workout IDs in Link column

   Note: Making workouts public is no longer a necessary step with the cookie-based authentication approach.

4. **Create Project Structure & Data Paths**
   - [x] The project follows a defined structure.
   - [x] **Primary Database**: `data/progress_tracking_data/migration_progress.db`
   - [x] **TCX Downloads**: `data/From_MapMyRun/TCX_downloads/`
   - [x] Internal logic has been standardized to use consistent path generation from a central configuration.
   ```
   mmr-to-strava/
   ├── src/
   │   ├── __init__.py
   │   ├── mmr_downloader.py        # New: Replaces Selenium/Simple downloaders
   │   ├── strava_uploader.py
   │   ├── csv_parser.py
   │   └── tcx_validator.py
   ├── utils/
   │   ├── __init__.py
   │   └── logger.py
   ├── data/
   │   ├── From_MapMyRun/
   │   │   ├── CSV_for_event_ID_extraction/
   │   │   └── TCX_downloads/
   │   ├── Processed/
   │   │   └── TCX_repaired/
   │   └── To_Strava/
   ├── tests/
   ├── logs/
   ├── config/
   │   ├── .env.example
   │   └── .env   # ignored by git
   ├── requirements.txt
   └── main.py
   ```

   Note: Project structure is complete, including `utils/logger.py` for central logging. The `selenium_downloader.py` has been removed in favor of `mmr_downloader.py`.

### Deliverables
- Working Python environment
- Valid credentials and tokens for both platforms
- MapMyRun workout history CSV file
- Updated project structure
- Validated access via a successful test download using the new cookie-based method.

## Phase 1: CSV Analysis & Workout Inventory (2-3 hours)

### Objectives
- Parse MapMyRun export CSV
- Create comprehensive workout inventory
- Identify data quality issues

### Tasks
1. **Create CSV Parser Module** (`src/csv_parser.py`)
   ```python
   class WorkoutInventory:
       def __init__(self, csv_path):
           self.df = pd.read_csv(csv_path)
           self.workout_ids = []
           
       def extract_workout_ids(self):
           # Extract IDs from Link column
           
       def generate_statistics(self):
           # Total workouts, date range, activity types
           
       def identify_missing_data(self):
           # Find workouts without links, etc.
   ```

2. **Data Analysis Script**
   - [x] Count total workouts
   - [x] Group by activity type
   - [x] Identify date ranges
   - [x] Find workouts without valid links
   - [x] Create summary report

3. **Create Download Queue**
   - [x] Generate list of workout IDs to download
   - [x] Save to `data/To_Strava/download_queue.json`
   - [x] Include metadata (date, activity type)

4. **Persist Inventory to SQLite**
   - [x] Create SQLite database at `data/progress_tracking_data/migration_progress.db` using SQLAlchemy
   - [x] Store workouts table (id, date, activity_type, download_path, mmr_status, strava_status)
   - [x] Use this DB for resume capability and deduplication across phases

### Deliverables
- [x] Workout inventory report
- [x] Download queue JSON file
- [x] Data quality assessment

## Phase 2: Authenticated TCX Downloader (`requests`) (3-4 hours)

### Objectives
- [x] Implement robust TCX download functionality using direct `requests` calls authenticated with a session cookie.
- [x] Handle errors, rate limiting, and progress tracking gracefully.

### Tasks
1. **Create Authenticated Downloader** (`src/mmr_downloader.py`)
   - [x] Create downloader class using `requests`.
   - [x] Implement `download_tcx` for single file downloads.
   - [x] Implement `batch_download` for multiple files.

2. **Implement Features**
   - [x] Progress tracking (using `tqdm`).
   - [x] Resume capability (skips already downloaded files).
   - [x] Error logging to the central logger.
   - [x] Rate limiting (2-3 second delays between requests).
   - [x] Retry logic for transient network errors.

### Testing
   - [x] Test with 5-10 workout IDs to verify the authentication and download process.
   - [x] Trial the first ~50 records before proceeding with full downloads to validate the process at scale.
   - [x] Verify TCX file validity and ensure `downloaded_flag` updates correctly in SQLite.
   - [x] Check error handling for invalid workout IDs or auth failures.

### Deliverables
- [x] A robust, working `requests`-based downloader.
- [x] All TCX files for the workouts downloaded successfully.
- [x] Updated SQLite DB with download statuses.
- [x] An error log for any failed downloads.

## Phase 3: (Removed)

This phase, previously for Selenium-based authenticated downloads, is now obsolete. The functionality has been merged into the new **Phase 2** using a more reliable cookie-based `requests` implementation.

## Phase 4: Data Validation & Preprocessing (3-4 hours)

### Objectives
- [x] Validate downloaded TCX files
- [ ] Fix common issues
- [ ] Prepare for Strava upload

### Tasks
1. **Create TCX Validator** (`src/tcx_validator.py`)
   - [x] Implement `validate` method using `tcxreader`.
   - [ ] `repair_tcx` method (for later).
   
2. **Validation Checks**
   - [x] Valid XML structure.
   - [x] Intelligent validation that correctly handles indoor activities (e.g., treadmill runs) by checking for duration or trackpoints, while quarantining corrupt files.
   - [x] Time series continuity.
   - [x] Heart rate data (if expected).
   - [x] Activity type mapping.

3. **Create Upload Manifest**
   - [ ] Map TCX files to original workout data
   - [ ] Prepare metadata for Strava upload
   - [ ] Group by upload batch (25 files)

### Deliverables
- [x] Validation report
- [ ] Fixed/cleaned TCX files
- [ ] Upload manifest JSON

## Phase 5: Strava Integration Setup (2-3 hours)

### Objectives
- [x] Implement Strava OAuth2 authentication
- [x] Set up stravalib client
- [x] Test API connectivity

### Tasks
1. **OAuth2 Implementation** (`src/strava_auth.py`)
   - [x] Create `StravaAuthenticator` class.
   - [x] Implement OAuth URL generation.
   - [x] Implement code-for-token exchange.
   - [x] Implement token refresh and persistence (`strava_token.json`).

2. **Local OAuth Server**
   - [x] Simple `HTTPServer` endpoint to handle redirect from Strava.
   - [x] Extract authorization code from the redirect URL.
   - [x] Store tokens securely in `config/` directory (ignored by git).

3. **Test Strava Connection**
   - [x] Authenticate successfully via the full browser flow.
   - [x] Fetch athlete profile to confirm connection.
   - [x] Verify that subsequent runs use the stored token instead of re-authenticating.

### Deliverables
- [x] Working Strava authentication flow.
- [x] Stored access/refresh tokens for session persistence.
- [x] Successful connection test results logged to the console.

## Phase 6: Strava Bulk Upload Implementation (4-5 hours)

### Objectives
- [x] Implement bulk upload to Strava
- [x] Handle rate limits
- [x] Manage duplicates

### Tasks
1. **Create Strava Uploader** (`src/strava_uploader.py`)
   - [x] Create `StravaUploader` class.
   - [x] Implement `upload_activity` for single file uploads.
   - [x] Implement `bulk_upload` for multiple files.

2. **Upload Features**
   - [x] Batch processing with user-configurable batch sizes.
   - [x] User confirmation prompt with single-file test option.
   - [x] **Advanced Duplicate Handling**: Implemented both proactive and reactive duplicate detection. The script first queries Strava for activities with similar metrics on the same day to prevent an upload attempt. It also correctly handles `409 Conflict` API responses from Strava if a duplicate is found post-upload.
   - [x] **Intelligent Rate Limit Handling**: The uploader now includes a robust backoff-and-retry mechanism. Upon receiving a `429 Too Many Requests` error, it will automatically pause for 15 minutes and then resume the operation, ensuring large batches can complete without interruption.
   - [x] Upload progress tracking with SQLite (`strava_status` updates).
   - [x] Error recovery for individual upload failures.

3. **Activity Enhancement**
   - [x] Set activity names from MapMyRun data, with a sensible fallback for untitled workouts (e.g., "Run on 2023-10-27").
   - [x] Add descriptions/notes.
   - [x] Normalize activity types to be Strava-compliant before upload.
   - [x] Preserve original timestamps via the TCX file.

### Deliverables
- [x] Working upload functionality integrated into `main.py`.
- [x] Upload status report (derived from SQLite).
- [x] Failed upload log in the main application log.

## Phase 7: Full Pipeline Integration (3-4 hours)

### Objectives
- Integrate all components
- Create end-to-end workflow
- Add user interface

### Tasks
1. **Main Application** (`main.py`)
   ```python
   class MapMyRunToStrava:
       def __init__(self, config_path):
           self.config = load_config(config_path)
           # self.inventory = WorkoutInventory(...)
           # self.downloader = MmrDownloader(...)
           # self.uploader = StravaUploader(...)
           
       def run_migration(self):
           # Execute full pipeline:
           # 1. Analyze CSV
           # 2. Download TCX files
           # 3. Validate files
           # 4. Authenticate with Strava
           # 5. Upload to Strava
   ```

2. **CLI Interface**
   - [x] Implemented a `--dry-run` command-line argument to simulate the entire migration pipeline without making any actual API calls to Strava. This is a critical pre-flight check.
   - [x] Added a `--csv-path` argument to allow specifying a custom location for the MapMyRun data export.
   - [x] Progress bars for all long-running operations.
   - [x] Status updates logged clearly to the console.

3. **Configuration Management**
   - [x] Environment variables (.env) loaded using python-dotenv.
   - [ ] Config file support
   - [ ] Command-line overrides

### Deliverables
- Integrated application
- User documentation
- Configuration templates

## Phase 8: Testing & Error Handling (3-4 hours)

### Objectives
- Comprehensive testing
- Robust error handling
- Final verification of the migration

### Tasks
1. **Architectural Robustness & Data Integrity**
   - **Database Schema Warning**: The project uses a fixed database schema defined by the `Workout` model. The application does not support automatic schema migrations. If the model is modified, the `data/progress_tracking_data/migration_progress.db` file **must be deleted** and rebuilt from the source CSV on the next run.
   - **Data Repair Utilities**: The scripts in the `utils/` directory are preserved for one-off data correction tasks (e.g., populating missing paths or re-validating files) and do not handle schema changes.

2. **Integration & Verification Testing**
   - [x] After implementing `--dry-run`, an end-to-end test has been performed, verifying the logs show the correct intended actions.
   - [x] After implementing improved duplicate handling, tests on known duplicates have confirmed they are correctly marked `skipped_already_exists`.
   - [x] A small batch has been verified end-to-end, checking Strava for data integrity (GPS, HR, timestamps) after the live upload.

3. **Performance Optimization**
   - [ ] Memory usage profiling during a large batch run (if needed).

### Deliverables
- Test suite results
- Performance report
- Bug fixes

## Phase 9: Documentation & Deployment (1-2 hours)

### Objectives
- Create final, accurate documentation
- Prepare for final execution

### Tasks
1. **Final Documentation Review**
   - [ ] Finalize `README.md` and this development plan after all code changes are complete. Ensure all descriptions are accurate and all checkboxes reflect the project's final state.
   - [ ] Add a brief "Troubleshooting" section to the `README` covering potential issues like cookie expiration or duplicate upload reports.

2. **Packaging & Cleanup**
   - [x] `requirements.txt` is finalized.
   - [ ] Before running the final migration, ensure no sensitive data or temporary files are committed to version control.

3. **User Guides**
   - [x] The `README.md` and `docs/how-to-download-tcx.md` serve as sufficient user guides.

### Deliverables
- Complete and accurate documentation.
- A clean project state, ready for execution.

## Phase 10: Post-Migration & Maintenance (2-3 hours)

### Objectives
- Verify successful migration
- Archive the project

### Tasks
1. **Verification**
   - [ ] After the full migration, compare the total count from the source CSV against the `upload_successful` and `skipped_already_exists` counts in the database.
   - [ ] Spot-check 10-20 activities on the Strava website to confirm data integrity.

2. **Cleanup**
   - [ ] Archive the downloaded TCX files and the final database.
   - [ ] Revoke the application's access in your Strava settings to secure your account.

3. **Final Audit**
   - [ ] **(Low Priority)** Create a post-migration audit utility (`utils/strava_duplicate_audit.py`).
   - [ ] This script will query the Strava API for all activities within the migration's date range.
   - [ ] It will identify and report any dates that contain more than one activity, allowing for a final manual inspection of potential duplicates.

4. **Future Enhancements**
   - No further enhancements are planned for this single-purpose tool.

### Deliverables
- Migration verification report.
- Archived project data.

## Risk Mitigation

### Potential Risks & Solutions

1. **MapMyRun Changes Website Structure or API**
   - **Risk**: The TCX export URL format (`/workout/export/{id}/tcx`) could change.
   - **Solution**: This is a low risk for a one-time migration. If it changes, the `base_url` in `MmrDownloader` can be easily updated. The core authentication method is more stable than UI elements.

2. **Rate Limiting/IP Blocking**
   - **Solution**: The plan already includes conservative rate limiting (2-3 second delays). We can implement exponential backoff if 429 "Too Many Requests" errors occur. Rotating user agents is also a good practice.

3. **Session Cookie Invalidation**
   - **Risk**: The `auth_token` cookie might expire during a long-running download process.
   - **Solution**: For a one-time migration of ~600 workouts, this is unlikely to be an issue if the script runs quickly. If it fails, the solution is simple: manually grab a new cookie and restart the script. The resume-safe design (using SQLite) ensures no work is lost.

4. **Authentication Failures**
   - **Risk**: The cookie is invalid or expired from the start.
   - **Solution**: The script should perform a test lookup on a known valid workout ID on startup. If it fails, it should exit immediately with a clear error message prompting the user to update their `MAPMYRUN_AUTH_TOKEN` in the `.env` file.

5. **Data Loss**
   - Solution: Always keep originals
   - Implement backups
   - Verification steps

## Success Metrics

- ✓ All workouts successfully migrated
- ✓ No data loss or corruption
- ✓ Execution time under 2 hours for 1000 workouts
- ✓ Less than 1% failure rate
- ✓ User can run with minimal technical knowledge (after the one-time cookie setup)

## Timeline Summary

- **Total Estimated Time**: 30-40 hours
- **Elapsed Time**: 2-3 weeks (working evenings/weekends)
- **Critical Path**: The new critical path is now Phases 0, 1, 2, 4, 5, 6.
- **Parallel Work**: Phases can be worked on sequentially as the plan is now much more linear and simplified.

## Current Project Status & Next Steps

The project's core features are complete and the application is stable and robust. All major development tasks outlined in this plan have been implemented. The application has been successfully tested with live data in batches, and the error handling, duplicate detection, and rate-limiting mechanisms have been proven to work effectively.

The application is now ready for the full, production migration of all remaining workouts.

The only remaining tasks are post-migration activities, as outlined in **Phase 10**, such as performing a final audit and archiving the project data. No further feature development is required to complete the primary goal of the migration.