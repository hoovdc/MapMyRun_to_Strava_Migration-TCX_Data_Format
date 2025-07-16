# MapMyRun to Strava Migration Development Plan

## Project Overview

This development plan outlines a phased approach to migrate fitness data from MapMyRun to Strava using Python automation. The project will extract workout data from MapMyRun, download detailed TCX files, and facilitate bulk upload to Strava.

## Project Clarifications
- I have about 600 workouts to sync.
- I plan to do this only once. In other words, I don't plan to do additional bulk transfers of this data in the future. I'll just use Strava to capture the data in the future.
- I don't want to use the MapMyRun API right now because I believe it would require a delay in my project for human approval of the granting of my API key.
- I am the only user of this project.

## Phase 0: Prerequisites & Setup (2-3 hours)

### Objectives
- Set up development environment
- Obtain necessary credentials
- Validate access to both platforms

### Tasks
1. **Development Environment Setup**
   - [ ] Install Python 3.8+ 
   - [ ] Create virtual environment: `python -m venv .venv`
   - [ ] Install required packages:
     ```bash
     pip install pandas requests selenium webdriver-manager stravalib python-dotenv beautifulsoup4
     ```
   - [ ] Install Chrome browser (if not present)
   - [ ] Install ChromeDriver or use webdriver-manager

2. **Credential Preparation**
   - [ ] MapMyRun credentials (username/password)
   - [ ] Create Strava API application at https://www.strava.com/settings/api
   - [ ] Note Client ID, Client Secret from Strava
   - [ ] Set Authorization Callback Domain to `localhost`
   - [ ] Create config/.env file (use .env.example if available)
   - [ ] Populate .env with real credential values (e.g., MAPMYRUN_USERNAME, STRAVA_CLIENT_ID)

3. **Data Export from MapMyRun**
   - [ ] Log into MapMyRun web interface
   - [ ] Export workout history CSV from https://www.mapmyfitness.com/workout/export/csv
   - [ ] Save as `data/From_MapMyRun/CSV_for_event_ID_extraction/mapmyrun_export.csv` in project directory
   - [ ] Verify CSV contains workout IDs in Link column
   - [ ] Temporarily make all workouts public in MapMyRun settings to simplify downloads

4. **Create Project Structure**
   ```
   mmr-to-strava/
   ├── src/
   │   ├── __init__.py
   │   ├── mmr_exporter.py
   │   ├── strava_uploader.py
   │   └── utils.py
   ├── data/
   │   ├── From_MapMyRun/
   │   │   ├── CSV_for_event_ID_extraction/
   │   │   └── TCX_downloads/
   │   └── To_Strava/
   ├── tests/
   ├── logs/
   ├── config/
   │   ├── .env.example
   │   └── .env   # ignored by git
   ├── requirements.txt
   └── main.py
   ```

### Deliverables
- Working Python environment
- Valid credentials for both platforms
- MapMyRun workout history CSV file
- Basic project structure

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

## Phase 2: Simple TCX Downloader (Public Workouts) (3-4 hours)

### Objectives
- Implement basic TCX download functionality
- Test with public workouts
- Handle errors gracefully

### Tasks
1. **Create Basic Downloader** (`src/simple_downloader.py`)
   ```python
   class SimpleDownloader:
       def __init__(self, output_dir='data/From_MapMyRun/TCX_downloads'):
           self.output_dir = Path(output_dir)
           self.session = requests.Session()
           
       def download_tcx(self, workout_id):
           # Download single TCX file
           
       def batch_download(self, workout_ids, delay=2):
           # Download multiple with rate limiting
   ```

2. **Implement Features**
   - [ ] Progress tracking
   - [ ] Resume capability using SQLite flags (skip workouts where `downloaded_flag` is true)
   - [ ] Error logging
   - [ ] Rate limiting (2-3 second delays)
   - [ ] Retry logic for failed downloads

### Testing
   - [ ] Test with 5-10 public workouts
   - [ ] Trial the first ~50 records before proceeding with full downloads to validate the process
   - [ ] Verify TCX file validity and ensure `downloaded_flag` updates correctly in SQLite
   - [ ] Check error handling

### Deliverables
- Working simple downloader
- Downloaded TCX files (public workouts)
- Updated SQLite DB with download statuses
- Error log for failed downloads

## Phase 3: Authenticated Downloader (Private Workouts) (4-5 hours)

### Objectives
- Implement Selenium-based authenticated download
- Handle MapMyRun login process
- Download private workouts

### Tasks
1. **Create Selenium Downloader** (`src/selenium_downloader.py`)
   ```python
   class AuthenticatedDownloader:
       def __init__(self, username, password):
           self.username = username
           self.password = password
           self.driver = None
           
       def login(self):
           # Handle MapMyRun authentication
           
       def download_with_auth(self, workout_ids):
           # Download private workouts
   ```

   Note: Since workouts will be made public for the duration of migration, this phase can be skipped by using the simple downloader from Phase 2 instead of authenticated Selenium-based downloads.

2. **Implement Robust Login**
   - [ ] Handle CAPTCHA (manual intervention if needed)
   - [ ] Cookie persistence
   - [ ] Session validation
   - [ ] Auto-retry on timeout

3. **Advanced Features**
   - [ ] Headless browser option
   - [ ] Download progress monitoring
   - [ ] Parallel download capability (optional if it easily improves speed without introducing difficult bugs)
   - [ ] Smart wait conditions

### Deliverables
- Authenticated downloader module
- All TCX files downloaded
- Comprehensive download report

## Phase 4: Data Validation & Preprocessing (3-4 hours)

### Objectives
- Validate downloaded TCX files
- Fix common issues
- Prepare for Strava upload

### Tasks
1. **Create TCX Validator** (`src/tcx_validator.py`)
   ```python
   class TCXValidator:
       def validate_tcx(self, file_path):
           # Use tcxreader library to check XML structure, verify required fields including GPS and heart rate data, and ensure data integrity
           
       def repair_tcx(self, file_path):
           # Fix common issues
           # Add missing metadata
   ```

2. **Validation Checks**
   - [ ] Valid XML structure
   - [ ] Presence of GPS data
   - [ ] Time series continuity
   - [ ] Heart rate data (if expected)
   - [ ] Activity type mapping

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
           
       def run_migration(self):
           # Execute full pipeline
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
   - [ ] Parallel downloads (with rate limiting)
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
   - [ ] Step-by-step migration guide
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
   - [ ] Revert MapMyRun workouts to private settings

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

1. **MapMyRun Changes Website Structure**
   - Solution: Use multiple selectors, implement fallbacks
   - Monitor for changes, update quickly

2. **Rate Limiting/IP Blocking**
   - Solution: Implement exponential backoff
   - Use rotating user agents
   - Respect rate limits

3. **Large Dataset Issues**
   - Solution: Implement chunking
   - Progress persistence via SQLite database (resume-safe)
   - Memory-efficient processing

4. **Authentication Failures**
   - Solution: Token refresh logic
   - Manual intervention options
   - Clear error messages

5. **Data Loss**
   - Solution: Always keep originals
   - Implement backups
   - Verification steps

## Success Metrics

- ✓ All workouts successfully migrated
- ✓ No data loss or corruption
- ✓ Execution time under 2 hours for 1000 workouts
- ✓ Less than 1% failure rate
- ✓ User can run with minimal technical knowledge

## Timeline Summary

- **Total Estimated Time**: 30-40 hours
- **Elapsed Time**: 2-3 weeks (working evenings/weekends)
- **Critical Path**: Phases 0-3 must be sequential
- **Parallel Work**: Phases 4-6 can overlap

## Next Steps

1. Set up development environment (Phase 0)
2. Export MapMyRun data
3. Begin with Phase 1 CSV analysis
4. Iterate through phases, testing continuously
5. Document issues and solutions as you progress