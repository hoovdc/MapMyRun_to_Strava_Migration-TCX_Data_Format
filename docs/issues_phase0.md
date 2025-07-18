# Issues Encountered in Phase 0: Prerequisites & Setup

## Overview
Phase 0 involves setting up the environment, credentials, CSV export, and validating access to MapMyRun and Strava. The main challenge has been validating MapMyRun access for TCX downloads. The original plan assumed temporarily making workouts public would allow simple, unauthenticated downloads (using requests in Phase 2). However, this failed, leading to a pivot to authenticated downloads using Selenium (borrowing from Phase 3). Despite multiple iterations, automation has not yet succeeded in downloading TCX files without manual intervention. Strava access is validated (creds in .env), but MapMyRun TCX extraction remains blocked.

This document logs all challenges, attempted solutions, failures, and the current state as of the latest conversation turn.

## Challenges
1. **Public Visibility Does Not Enable Unauthenticated TCX Downloads**:
   - Description: Even after setting workouts to public in MapMyRun settings, accessing TCX URLs (e.g., https://www.mapmyrun.com/workout/export/8625606887/tcx) or base workout pages (e.g., https://www.mapmyrun.com/workout/8625606887) requires login in incognito/private browsers. This defeats the simplification in the plan to skip authenticated downloads.
   - Impact: Cannot use simple requests-based downloader (Phase 2); must use authenticated method.
   - Status: Unresolved without auth; led to pivot.

2. **Selenium Login Automation Failures**:
   - Timeout on Login Elements: Script times out waiting for 'email', 'password', or submit button (generic "Message: " error from Selenium).
   - Redirects to Dashboard: After manual login, page redirects to https://www.mapmyrun.com/dashboard, but script doesn't detect this and still waits for login form elements (which don't exist on dashboard).
   - Cookie Consent Popup: Site repeatedly prompts for cookie acceptance (from securiti.ai), blocking automation.
   - Recaptcha Detection: Site sometimes shows recaptcha (anti-bot measure), requiring manual solve.
   - Session Persistence: Logins don't stick across runs, requiring manual login each time.
   - Verbose Logs Overflowing Terminal: Error dumps (e.g., full page source) make output hard to read.

3. **Other Technical Issues**:
   - ModuleNotFoundError: 'selenium' not found (despite pip install).
   - ValueError: Credentials not loaded from .env.
   - Element Not Interactable: Fields not clickable due to timing or visibility.
   - Password Manager Unavailable: Selenium's isolated Chrome instance doesn't load user extensions/profiles.
   - Log Structure Errors: Initial log paths used hyphens instead of slashes, causing invalid directories.

- General: MapMyRun's site (part of Under Armour) has dynamic elements, redirects, and anti-automation (recaptcha, consents), making Selenium tricky. About 600 workouts mean manual downloads are feasible but tedious as a fallback.

## Attempted Solutions and Failures
All attempts focused on src/selenium_downloader.py unless noted. Iterations built on each other, but none fully automated TCX downloads without manual steps.

1. **Initial Implementation (Basic Selenium Login)**:
   - Solution: Created AuthenticatedDownloader class with setup_driver, login (using WebDriverWait for elements), download_tcx, batch_download.
   - Failure: ModuleNotFoundError for selenium (venv had it, but run without activation). Fixed by ensuring venv activation.
   - Log: "No module named 'selenium'".

2. **Credential Loading Fix**:
   - Solution: load_dotenv with path to config/.env.
   - Failure: ValueError if creds missing. Fixed, but led to login timeouts.
   - Log: "MapMyRun credentials are required".

3. **Interactability and Headless Fixes**:
   - Solution: Switched to non-headless, used element_to_be_clickable, increased timeouts (e.g., 60s).
   - Failure: "Element not interactable" (timing issues). Manual intervention worked, but automation failed on subsequent runs.
   - Log: "element not interactable (Session info: chrome=...)".

4. **Cookie Consent and Recaptcha Handling**:
   - Solution: Added try to click consent button (by ID/class), pause for manual recaptcha solve if detected in source.
   - Failure: Consent not always detected; recaptcha triggers on repeats. Manual accept/solve works, but redirects to dashboard cause timeout on email wait.
   - Log: "Recaptcha detected" or timeout "Message: ".

5. **Session Persistence Attempts**:
   - Solution: Added user-data-dir for Chrome profile persistence, pickle for saving/loading cookies after login.
   - Failure: Sessions don't persist reliably (new run starts fresh); manual login needed each time. User profile option (for extensions) conflicts with some systems.
   - Log: Redirect to dashboard not detected, still waits for login elements.

6. **Diagnostic Logging Improvements**:
   - Solution: Created utils/logger.py for date-nested logs (YYYY-MM/MM-DD/DD-HH00/HHMM.log), git-ignored. Switched prints to logger.info/error, truncated source dumps, added step traces (e.g., "Step: Waiting for email").
   - Failure: Logs still verbose in early versions; fixed with level=ERROR for console, full in file. Structure fixed from hyphens to slashes.
   - Log: Overflow reduced, but errors like "Login error: Message: " persist without more context.

7. **Redirect and Logged-In Detection**:
   - Solution: Check current_url for 'dashboard' after get(), skip login if true. Added is_logged_in method checking for dashboard element.
   - Failure: Detection misses some cases (e.g., if URL varies or element not present immediately), leading to timeout.
   - Log: "Current URL after get(): https://www.mapmyrun.com/dashboard" but then "Waiting for email field..." timeout.

8. **Other Fixes**:
   - Updated login URL to mapmyfitness.com (redirect target).
   - Suppressed Chrome logs (--log-level=3).
   - Added manual_mode flag to pause at key points.
   - Failure: Still requires manual login/cookie accept each run; no TCX downloaded automatically.

## Current State
- **Successes**: Environment setup, CSV export/verification, Strava creds, project structure (including utils/logger.py) are complete. Manual login in Selenium browser works and redirects to dashboard. Logs are now structured and git-ignored.
- **Blocking Issue**: Automation can't consistently skip login or handle the form without timeout, even with persistence. TCX download step isn't reached reliably.
- **Workarounds Tried**: Manual intervention for login/cookies/recaptcha works, but defeats automation goal. Persistent profile saves session, but detection fails.
- **Latest Log Summary** (from your attached): Script navigates, waits for email (times out with "Message: "), dumps page source (dashboard HTML with scripts/recaptcha). No TCX downloaded.
- **Risks**: Continued iterations may hit MapMyRun's rate limits or anti-bot blocks. For 600 workouts, manual batch exports via browser might be faster.

## Next Steps (When Resuming)
- Test with use_user_profile=True and manual_mode=True to use extensions and pause for input.
- If fails, extract cookies manually from browser dev tools and load into requests.session for non-Selenium downloads.
- Fallback: Manual TCX exports in batches from MapMyRun web, then proceed to Phase 4 (validation) and Strava upload.
- Update plan to move authenticated downloader to Phase 2 as primary method.


## Phase 1: Database Schema Repair Failures

### Challenge: Persistent `OperationalError` during Database Repair

*   **Description**: After implementing the database-driven workflow, a one-time utility script (`utils/repair_database.py`) was created to update the existing database schema. The goal was to rename the old `Status` column to `mmr_status` and add a new `strava_status` column. However, every attempt to run this script failed with the same error: `sqlite3.OperationalError: no such column: workouts.mmr_status`.
*   **Impact**: The database schema could not be updated, blocking all subsequent data repair and validation steps. The script repeatedly crashed before it could populate missing `download_path` links or re-validate existing TCX files.
*   **Root Cause**: A fundamental conflict between SQLAlchemy's Object-Relational Mapper (ORM) and the physical database file. The application's `Workout` model (in `src/database_manager.py`) defines the schema in Python code, explicitly expecting a column named `mmr_status`. The moment the repair script imported this model, SQLAlchemy's metadata registry was primed with this expectation. This "poisoned" the context, causing all checks against the actual database (which still had the old `Status` column) to fail in confusing ways. The script was unable to see the reality of the on-disk schema because the ORM's view of the world took precedence.

### Attempted Solutions and Failures

1.  **Session Refresh**:
    *   **Solution**: The initial theory was that the SQLAlchemy session had a stale view of the schema. The fix involved closing the session after the migration and creating a new one for the data repair step.
    *   **Failure**: Failed with the same `OperationalError`. The problem occurred because the schema migration step itself was being skipped incorrectly, so refreshing the session afterwards had no effect.

2.  **Low-Level Schema Inspection (`PRAGMA`)**:
    *   **Solution**: The next theory was that SQLAlchemy's `inspector` was providing cached information. The fix was to use a direct SQL `PRAGMA table_info()` query to get the "true" column list from the database, bypassing the inspector.
    *   **Failure**: Failed with the same error. This revealed that the core issue was the ORM context being established at the moment of import, not at run time, making even direct queries unreliable within that context.

3.  **Conditional Metadata Creation**:
    *   **Solution**: To prevent the ORM from establishing its context, a `skip_metadata_creation` flag was added to the `DatabaseManager`. The repair script used this flag to try and get a "clean" connection.
    *   **Failure**: Failed with the same error. This confirmed the root cause: simply importing the `Workout` model anywhere in the script's execution path was enough to create the schema conflict, regardless of how the `DatabaseManager` was initialized.

### Next Steps (The Definitive Fix)

*   **Step 1: Create a Pure SQL Migration Script**: A new, temporary utility script (`utils/direct_sql_migrate.py`) will be created.
    *   This script will use Python's standard `sqlite3` library, not SQLAlchemy.
    *   It will **not import any project modules** (`DatabaseManager`, `Workout`, etc.) to avoid the ORM conflict.
    *   It will perform the `ALTER TABLE` operations directly and reliably.
*   **Step 2: Run the Main Repair Script**: After the schema is corrected by the pure SQL script, the existing `utils/repair_database.py` will be run. Freed from the schema migration task, it will now successfully execute its intended purpose: populating download links and re-validating TCX files.