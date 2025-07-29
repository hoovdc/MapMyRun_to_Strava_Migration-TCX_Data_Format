# Phase 8 - Post-Launch Stabilization and Debugging

This document outlines the root causes and resolutions for issues discovered during the high-volume stress test conducted in Phase 8, along with enhanced diagnostic and resolution strategies.

---

## Priority Assessment and Testing Strategy

### **Priority 1: Diagnostic Enhancement (Low Risk)**
- Issue 2 diagnostic improvements should be implemented first as they provide immediate value without changing core logic
- Can be safely deployed and tested with existing failed uploads

### **Priority 2: Rate Limit Investigation (Medium Risk)**  
- Issue 1 requires investigation phase before implementation
- Changes affect retry logic and could impact upload flow
- Requires controlled testing with deliberate rate limit triggering

### **Prerequisites**
- Working development environment with access to Strava API
- Test dataset of problematic TCX files (use `utils/get_failed_validation_ids.py`)
- Ability to trigger controlled rate limits without affecting production data
- Log monitoring setup to capture diagnostic information

### **Success Criteria**
- **Issue 1**: Rate limit exceptions properly caught and handled with appropriate cooldowns
- **Issue 2**: Clear diagnostic information logged for rejected uploads, including file validation results
- **Testing**: Successful completion of controlled rate-limit test scenarios
- **Monitoring**: API call counting provides early warning before limits are reached

### **Testing Strategy**
- **Controlled Rate-Limit Testing**:  
  - *Stage 1 (15-minute window)*: Execute a small burst of 5-10 uploads in rapid succession to intentionally exceed the short-term limit.  
  - *Stage 2 (Daily window)*: Follow with a wider burst (≈600 API calls spread over ~60 minutes) to probe the daily cap.  
  - *Note*: Each duplicate-check issues extra API calls, so uploads ≠ total calls.
- **File-Rejection Testing**: Test with known problematic TCX files to trigger "Uploader is None" scenarios.  
- **API-Calls Monitoring**: Track total API calls per batch—including calls from duplicate checks—to validate rate-limiting assumptions.
- Monitor console progress via existing `tqdm` bars during tests to align with user preferences for visible indications
- Use utilities like `utils/get_failed_validation_ids.py` to identify or simulate problematic files for testing

---

## Issue 1: Rate-Limit Handler Investigation Required

- **Symptom:** During the batch upload of 100 workouts, the application began failing with `429 Client Error: Too Many Requests` but never initiated the 15-minute cooldown period. The logs show that these rate-limit errors started occurring during the proactive duplicate check.

- **Context & Analysis:** The rate limit was hit after approximately 63 API calls. This confirms that a fixed-time delay between uploads is insufficient, as it fails to account for the variable number of API calls made during the duplicate-checking phase.

- **Current Code Analysis:** Review of `src/strava_uploader.py` reveals that rate limit handling **is already implemented** in the `_is_duplicate()` method (lines 70-76) and similarly in `upload_activity()` (lines ~189-197). However, the handler may not be triggering due to exception format or API response structure changes.

- **Root Cause Hypothesis:** The issue is likely one of:
  1. **Exception Structure**: The `stravalib` exceptions might not have the expected `response.status_code` attribute structure
  2. **Exception Type**: Rate-limit errors might be wrapped in a different exception type that doesn't match current catch logic  
  3. **API Response Changes**: Strava's API response format may have changed since implementation
  4. **Dedicated `RateLimitExceeded` Exception**: Newer `stravalib` versions raise `stravalib.exc.RateLimitExceeded`, which may bypass current checks.

- **Immediate Fix Example:**
  ```python
  # In both _is_duplicate() and upload_activity() methods
  try:
      # ... existing API call logic ...
  except RateLimitExceeded as e:
      logger.error(f"Rate limit exceeded (dedicated exception): {e}")
      self._handle_rate_limit()
      return self._is_duplicate(workout)  # Retry after waiting
  except Exception as e:
      # Enhanced diagnostic logging
      logger.error(f"Exception in _is_duplicate for workout {workout.workout_id}: "
                  f"Type: {type(e).__name__}, Message: {str(e)}")
      
      # Existing fallback logic for status code checking
      response = getattr(e, 'response', None)
      if response and hasattr(response, 'status_code') and response.status_code == 429:
          if hasattr(response, 'headers'):
              logger.debug(f"Rate limit headers: {dict(response.headers)}")
          self._handle_rate_limit()
          return self._is_duplicate(workout)
      
      logger.error(f"An unexpected error occurred during duplicate check for workout {workout.workout_id}: {e}. Proceeding with upload attempt.")
      return None
  ```

- **Resolution Plan:**
  - [ ] **Phase 1: Enhanced Diagnostic Logging**
    - [ ] **Add specific `RateLimitExceeded` exception handling** to `_is_duplicate()` and `upload_activity()` methods before general exception catching
    - [ ] Add detailed exception logging to capture `type(e).__name__`, `str(e)`, and `repr(e)` for all unhandled exceptions.
    - [ ] When a `response` object exists, log its key headers (`Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Usage`) for immediate cooldown insights.
    - [ ] Implement API-call counting across all methods to track proximity to both 15-minute and daily limits.
    - [ ] Use `logger.debug()` / `logger.error()` so that *all* diagnostics are written to log files, never to the console.
  
  - [ ] **Phase 2: Adaptive Rate Limit Detection**  
    - [ ] Based on diagnostic findings, update rate limit detection logic to handle actual exception patterns
    - [ ] Implement more robust exception type checking beyond just status codes
    - [ ] Add fallback detection for rate limit scenarios that don't match expected patterns

  - [ ] **Phase 3: Enhanced Rate Limiting Strategy**
    - [ ] Implement dynamic cooldowns that derive the wait period from Strava's `Retry-After` or `X-RateLimit-Reset` headers (fallback 900 s).
    - [ ] Add inter-batch delays for high-volume uploads based on running call counts.
    - [ ] Consider reducing maximum batch size from 300 to 50 for safer operation.
    - [ ] **API Call Counter Implementation:**
      ```python
      # Add to StravaUploader.__init__
      self.api_call_count = 0
      self.api_call_start_time = time.time()
      
      def _count_api_call(self, operation_name: str):
          """Track API calls for rate limit monitoring"""
          self.api_call_count += 1
          elapsed = time.time() - self.api_call_start_time
          logger.debug(f"API call #{self.api_call_count} ({operation_name}) - {elapsed:.1f}s elapsed")
          
          # Warning at 80% of 15-min limit (80 calls)
          if self.api_call_count % 20 == 0:
              logger.info(f"API usage: {self.api_call_count} calls in {elapsed/60:.1f} minutes")
      ```

---

## Issue 2: Enhanced Diagnostics for Immediate Upload Rejections  

- **Symptom:** A large number of uploads failed consecutively with the error `Upload finished in an unknown state or was rejected mid-process. Uploader is None.` This happened before the rate limit was explicitly hit.

- **Context & Analysis:** This error indicates that the Strava API is rejecting the upload request immediately, and the `stravalib` library returns `None` instead of an uploader object. This is not a rate-limit issue but is likely caused by problematic TCX file data that Strava's servers reject on initial inspection.

- **Current Implementation:** The code already handles this scenario safely (lines 155-157 in `src/strava_uploader.py`) but provides limited diagnostic information for troubleshooting.

- **Resolution Plan:**
  - [ ] **Enhanced Diagnostic Logging in `upload_activity()` method:**
    - [ ] Locate the `if uploader is None:` block in `src/strava_uploader.py`.
    - [ ] Replace the current basic exception with comprehensive diagnostic logging and enhanced error message.
    - [ ] Add file-validation checks (leveraging `tcx_validator.py`) to provide context about TCX file quality.
    - [ ] Log `uploader.error` (first ≈2 KB) if available, redacting any sensitive tokens.
    - [ ] Ensure *all* diagnostic information is logged to files only via `logger.debug()` / `logger.error()`.

  - [ ] **Implementation Details:**
    ```python
    if uploader is None:
        # Comprehensive diagnostic logging (file-only)
        error_msg = (
            f"Upload immediately rejected by Strava for workout {workout.workout_id}. "
            f"TCX file: {workout.download_path}"
        )
        logger.error(error_msg)

        # Capture uploader.error when present (truncate to 2 KB)
        if hasattr(uploader, "error") and uploader.error:
            logger.debug(f"Uploader error (truncated): {uploader.error[:2048]}")

        # File diagnostics
        if os.path.exists(workout.download_path):
            file_size = os.path.getsize(workout.download_path)
            logger.debug(f"TCX file exists, size: {file_size} bytes")

            # Use existing TcxValidator class properly
            from src.tcx_validator import TcxValidator
            validator = TcxValidator()
            is_valid = validator.validate(workout.download_path)
            logger.debug(f"TCX validation result: {'PASSED' if is_valid else 'FAILED'}")
        else:
            logger.error("TCX file does not exist at specified path")

        raise ActivityUploadFailed(
            f"{error_msg}. Possible causes: corrupt file, invalid data, or API rejection."
        )
    ```

---

## Diagnostic Implementation Priority

1. **Enhanced Diagnostics (Issue 2, Immediate)**: Low-risk improvements that provide immediate troubleshooting value
2. **Issue 1 Investigation (Next)**: Systematic investigation of actual rate-limit exception patterns  
3. **Robust API Call Pattern (Future)**: Comprehensive refactoring for long-term stability
4. **Batch Processing Improvements (Future)**: Optimise for high-volume scenarios

This phased approach ensures that immediate diagnostic value is gained while building toward more robust long-term solutions.

---

## Deprioritized: Future Considerations for Enhanced Stability

These tasks arose from broader analysis but are deprioritized to avoid scope creep in Phase 8. They focus on long-term improvements and should be revisited only after core issues are resolved, potentially in a future phase.

### **Robust API Call Pattern**
To address both issues systematically, implement a wrapper pattern for all Strava API calls:

- [ ] **Create `_robust_api_call()` method** in `StravaUploader` class:
  - Centralizes rate limit detection and handling
  - Provides consistent retry logic across all API interactions  
  - Logs comprehensive diagnostic information to files
  - Supports different retry strategies for different call types

- [ ] **Update `_is_duplicate()` and `upload_activity()`** to use the robust wrapper
- [ ] **Add API call tracking** to monitor rate limit approach across entire upload session

### **Batch Processing Improvements**  
- [ ] **Reduce maximum batch size** from 300 to 50 to minimize rate limit exposure
- [ ] **Add inter-batch delays** based on API call count rather than fixed time
- [ ] **Implement batch-level error recovery** to handle partial batch failures gracefully

These deprioritized items enhance the 'Advanced Error Handling' features in README.md but are not essential for immediate post-launch stabilization.
