# Phase 8 - Post-Launch Stabilization and Debugging

This document outlines the root causes and resolutions for issues discovered during the high-volume stress test conducted in Phase 8, along with enhanced diagnostic and resolution strategies.

---

## Priority Assessment and Testing Strategy

### Updated Priorities (Post-Implementation)
- Issue 1 (Rate Limits): Resolved with enhanced handling, API counting, and dynamic cooldowns. Verified in small tests; pending high-volume confirmation.
- Issue 2 (Upload Rejections): Enhanced diagnostics implemented. Extended to address persistent "Uploader is None" rejections, likely due to Strava-specific TCX validation.
- New Focus: Manual diagnostics and TCX repairs before scaled testing.

### **Testing Strategy** (Updated)
- **Controlled Rate-Limit Testing**: 
  - Stage 1 (15-minute window): Execute a small burst of 5-10 uploads in rapid succession to intentionally exceed the short-term limit.  
  - Stage 2 (Daily window): Follow with a wider burst (≈600 API calls spread over ~60 minutes) to probe the daily cap.  
  - Note: Each duplicate-check issues extra API calls, so uploads ≠ total calls.
- **File-Rejection Testing**: Test with known problematic TCX files to trigger "Uploader is None" scenarios.  
- **API-Calls Monitoring**: Track total API calls per batch—including calls from duplicate checks—to validate rate-limiting assumptions.
- **Manual Web Upload Test**: Upload a failed TCX directly on Strava.com to get exact rejection reason (e.g., "invalid format").
- **Log Review**: Examine full log for diagnostics on rejected workouts (file size, validation result).
- Monitor console progress via existing `tqdm` bars during tests to align with user preferences for visible indications.
- Use utilities like `utils/get_failed_validation_ids.py` to identify or simulate problematic files for testing.

## Issue 1: Rate-Limit Handler (Resolved)

- **Symptom**: (Original description...)
- **Resolution**: Implemented API call counting, specific exception handling for RateLimitExceeded and Fault with 429, dynamic cooldowns using Retry-After or calculated reset intervals. Proactive warnings at 80% limits.
- **Status**: Verified in small batches; high-volume test pending.

## Issue 2: Enhanced Diagnostics for Immediate Upload Rejections (Extended & Ongoing)

- **Symptom**: Uploads failed with "Uploader is None" before rate limits, likely due to TCX data Strava rejects.
- **Context & Analysis**: (Original...) Extended: Local validation passes, but Strava rejects immediately—likely format mismatches (e.g., missing tags, indoor activity quirks).
- **Resolution Plan** (Updated with Progress):
  - [x] Enhanced logging with file diagnostics and validation.
  - [ ] Manual web upload test to get Strava's exact error.
  - [ ] Review full log for rejected workouts.
  - [ ] Repair TCX (e.g., add missing elements) and retry one.
- **Status**: Diagnostics in place; manual steps needed to confirm root cause.

## **NEXT STEPS: Verification and Repairs**

1. Manual Web Upload Test: Upload a failed TCX (e.g., 8609714920.tcx) on strava.com/upload/manual for exact error.
2. Log Review: Check latest log for diagnostics on that ID.
3. Repair & Retry: Based on error, edit TCX and test single upload (menu option 1).
4. Scaled Testing: Once fixed, run larger batches monitoring for non-rate issues.

## Archived and Completed Details

### Original Priority Assessment (Completed)
- Priority 1: Diagnostic enhancements for Issue 2 implemented first for immediate value.
- Priority 2: Rate limit investigation for Issue 1 completed with controlled testing.

### Original Issue 1 Details (Resolved)
- Symptom: 429 errors without cooldown during duplicate checks.
- Context: Hit after ~63 calls; fixed-time delays insufficient.
- Hypothesis: Exception structure/type mismatches; resolved with broader catching and dynamic handling.

### Original Issue 2 Details (Extended)
- Symptom: "Uploader is None" rejections before rate limits.
- Context: Immediate API rejections likely from TCX data; enhanced with diagnostics.

### Deprioritized Items (Integrated or Deferred)
- Robust API call wrapper: Integrated into exception handling.
- Batch improvements: Deferred; current setup sufficient post-fixes.
