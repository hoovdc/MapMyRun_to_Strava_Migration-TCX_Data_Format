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
   - [x] Verify CSV contains workout IDs in Link column

   Note: Making workouts public is no longer a necessary step with the cookie-based authentication approach.

4. **Create Project Structure**
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
   - [ ] Count total workouts
   - [ ] Group by activity type
   - [ ] Identify date ranges
   - [ ] Find workouts without valid links
   - [ ] Create summary report

3. **Create Download Queue**
   - [ ] Generate list of workout IDs to download
   - [ ] Save to `data/To_Strava/download_queue.json`
   - [ ] Include metadata (date, activity type)

4. **Persist Inventory to SQLite**
   - [ ] Create SQLite database at `data/migration_progress.db` using SQLAlchemy
   - [ ] Store workouts table (id, date, activity_type, download_path, downloaded_flag, uploaded_flag)
   - [ ] Use this DB for resume capability and deduplication across phases

### Deliverables
- Workout inventory report
- Download queue JSON file
- Data quality assessment

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
- [ ] All TCX files for the workouts downloaded successfully.
- [ ] Updated SQLite DB with download statuses.
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
   - [x] Presence of GPS data.
   - [x] Time series continuity.
   - [x] Heart rate data (if expected).
   - [x] Activity type mapping.

3. **Create Upload Manifest**
   - [ ] Map TCX files to original workout data
   - [ ] Prepare metadata for Strava upload
   - [ ] Group by upload batch (25 files)

### Deliverables
- Validation report
- Fixed/cleaned TCX files
- Upload manifest JSON

## Phase 5: Strava Integration Setup (2-3 hours)

### Objectives
- Implement Strava OAuth2 authentication
- Set up stravalib client
- Test API connectivity

### Tasks
1. **OAuth2 Implementation** (`src/strava_auth.py`)
   ```python
   class StravaAuthenticator:
       def __init__(self, client_id, client_secret):
           self.client = Client()
           
       def get_authorization_url(self):
           # Generate OAuth URL
           
       def exchange_code_for_token(self, code):
           # Get access token
           
       def refresh_token(self):
           # Handle token refresh
   ```

2. **Local OAuth Server**
   - [ ] Simple Flask/FastAPI endpoint
   - [ ] Handle redirect from Strava
   - [ ] Extract authorization code
   - [ ] Store tokens securely

3. **Test Strava Connection**
   - [ ] Authenticate successfully
   - [ ] Fetch athlete profile
   - [ ] List existing activities

### Deliverables
- Working Strava authentication
- Stored access/refresh tokens
- Connection test results

## Phase 6: Strava Bulk Upload Implementation (4-5 hours)

### Objectives
- Implement bulk upload to Strava
- Handle rate limits
- Manage duplicates

### Tasks
1. **Create Strava Uploader** (`src/strava_uploader.py`)
   ```python
   class StravaUploader:
       def __init__(self, access_token):
           self.client = Client(access_token=access_token)
           
       def upload_activity(self, tcx_path, activity_name=None):
           # Upload single activity
           
       def bulk_upload(self, tcx_files, batch_size=25):
           # Upload in batches
   ```

2. **Upload Features**
   - [ ] Batch processing (25 at a time)
   - [ ] Gradual upload: Start with 1 single record for manual audit, then 5 more, gradually increasing batch size
   - [ ] Duplicate detection
   - [ ] Rate limit handling (100 requests/15 min)
   - [ ] Upload progress tracking with SQLite (`uploaded_flag` updates)
   - [ ] Error recovery

3. **Activity Enhancement**
   - [ ] Set activity names from MapMyRun data
   - [ ] Add descriptions/notes
   - [ ] Set activity type correctly
   - [ ] Preserve original timestamps

### Deliverables
- Working upload functionality
- Upload status report (derived from SQLite)
- Failed upload log

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
   - [ ] Command-line arguments
   - [ ] Interactive mode
   - [ ] Progress bars
   - [ ] Status updates

3. **Configuration Management**
   - [ ] Environment variables (.env) - load using python-dotenv in scripts
   - [ ] Config file support
   - [ ] Command-line overrides

### Deliverables
- Integrated application
- User documentation
- Configuration templates

## Phase 8: Testing & Error Handling (3-4 hours)

### Objectives
- Comprehensive testing (start with essential unit tests only, add more if needed)
- Robust error handling
- Performance optimization

### Tasks
1. **Unit Tests**
   - [ ] Test each module independently
   - [ ] Mock external services
   - [ ] Edge case handling

2. **Integration Tests**
   - [ ] End-to-end workflow test
   - [ ] Error recovery scenarios
   - [ ] Large dataset testing

3. **Performance Optimization**
   - [ ] Batch processing optimization
   - [ ] Memory usage profiling

### Deliverables
- Test suite
- Performance report
- Bug fixes

## Phase 9: Documentation & Deployment (2-3 hours)

### Objectives
- Create comprehensive documentation
- Package for easy deployment
- Create user guides

### Tasks
1. **Documentation**
   - [ ] README.md with quick start
   - [ ] Detailed user guide
   - [ ] API documentation
   - [ ] Troubleshooting guide

2. **Packaging**
   - [ ] Requirements.txt finalization
   - [ ] Docker container (optional)
   - [ ] Setup.py for installation

3. **User Guides**
   - [ ] Step-by-step migration guide, including how to get the auth token.
   - [ ] Video tutorial (optional)
   - [ ] FAQ section

### Deliverables
- Complete documentation
- Packaged application
- User guides

## Phase 10: Post-Migration & Maintenance (Ongoing)

### Objectives
- Verify successful migration
- Handle edge cases
- Maintain compatibility

### Tasks
1. **Verification**
   - [ ] Compare MapMyRun vs Strava totals
   - [ ] Spot-check activity details
   - [ ] Verify all data transferred

2. **Cleanup**
   - [ ] Archive TCX files
   - [ ] Clean up temporary files
   - [ ] Document any issues
   - [ ] Revert MapMyRun workouts to private settings (if they were ever made public)

3. **Future Enhancements**
   - [ ] Auto-sync new activities
   - [ ] Support for other platforms
   - [ ] GUI version

### Deliverables
- Migration verification report
- Archived data
- Enhancement roadmap

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

## Next Steps

1. Set up development environment (Phase 0)
2. Export MapMyRun data and extract auth cookie
3. Implement Phase 1: CSV Analysis & Workout Inventory.
4. Run the full batch download to acquire all ~600 TCX files.
5. Proceed with the remaining tasks in Phase 4 (Data Validation & Preprocessing).
6. Continue through the remaining phases of the project.