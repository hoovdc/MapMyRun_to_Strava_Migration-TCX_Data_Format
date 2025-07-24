# Phase 8 - Post-Launch Stabalization and Debugging

This document outlines the root causes and resolutions for issues discovered during the high-volume stress test conducted in Phase 8.

---

### Issue 1: Rate-Limit Handler Not Triggered

- **Symptom:** During the batch upload of 100 workouts, the application began failing with `429 Client Error: Too Many Requests` but never initiated the 15-minute cooldown period. The logs show that these rate-limit errors started occurring during the proactive duplicate check.

- **Context & Analysis:** The rate limit was hit after approximately 63 API calls. This confirms that a fixed-time delay between uploads is an insufficient strategy, as it fails to account for the variable number of API calls made during the duplicate-checking phase. This highlights the need for a robust, *reactive* rate-limit handler that responds to API feedback rather than relying on a predetermined pause.

- **Root Cause Analysis:** The `_handle_rate_limit()` method is designed to be called when a rate-limit exception occurs during the main upload process. However, the test revealed that the API calls within the `_is_duplicate()` method were the first to hit the limit. The `_is_duplicate()` method was designed to catch this exception and log it, but it did **not** call `_handle_rate_limit()`. Instead, it would simply proceed to the next step (the actual upload attempt), which was then guaranteed to fail because the rate limit was already active.

- **Resolution Plan:**
  - [ ] **Modify `_is_duplicate()` in `src/strava_uploader.py`:**
    - [ ] In the `except Exception` block, add logic to reliably detect a rate-limit error (e.g., by inspecting `e.response.status_code == 429`).
    - [ ] If it is a rate-limit error, call `self._handle_rate_limit()` to trigger the cooldown.
    - [ ] After the cooldown, recursively call `return self._is_duplicate(workout)` to automatically retry the check.

---

### Issue 2: Mass Failures with "Uploader is None"

- **Symptom:** A large number of uploads failed consecutively with the error `Upload finished in an unknown state or was rejected mid-process. Uploader is None.` This happened before the rate limit was explicitly hit.

- **Root Cause Analysis:** This error indicates that the Strava API is rejecting the upload request immediately, and the `stravalib` library returns `None` instead of an uploader object. This is not a rate-limit issue but is likely caused by a problem with the data being sent, such as a malformed or invalid TCX file that Strava's servers reject on initial inspection. The current error handling for this is safe (it logs the error and moves on), but it doesn't help identify the problematic files.

- **Resolution Plan:**
  - [ ] **Enhance logging in `upload_activity()` in `src/strava_uploader.py`:**
    - [ ] Locate the `if uploader is None:` block.
    - [ ] Inside this block, modify the `ActivityUploadFailed` exception that is raised to include the workout ID and its TCX file path.
    - [ ] This will ensure the existing error-handling logic logs a more informative message, clearly identifying the specific file that was rejected.
