# MapMyRun to Strava Migration: Record Status Audit Plan

## Quick Reference

| **Audit Scope** | **Time Estimate** | **Primary Output** | **Success Target** |
|-----------------|-------------------|--------------------|--------------------|
| 1,234 MMR Activities | ~~7.5 hours~~ **2 hours total** | Executive Dashboard | 95%+ migration rate |

### ⚡ Efficiency Optimizations Applied
- **🎯 Database-First Approach**: Use existing `utils/db_status_report.py` and `main.py` status summary
- **🔄 Reuse Existing Logic**: Leverage `StravaUploader._is_duplicate()` instead of building new matching
- **📊 Smart API Usage**: 15-20 targeted queries instead of 1000+ comprehensive catalog
- **⏱️ 75% Time Reduction**: 2 hours vs. 7.5 hours through strategic reuse
- **🚀 95% API Reduction**: Minimize rate limit risk and focus on actionable insights

### Key Deliverables At-a-Glance
- ✅ **Master Status Table**: Overall migration success rate with breakdown
- 📊 **Activity Type Analysis**: Success rates by activity type (running, cycling, etc.)  
- 🔍 **Failed Migration Details**: Specific activities requiring attention
- 🚫 **Garmin Exclusions**: Activities to exclude from migration assessment
- ⚡ **Action Items**: Prioritized list of retry candidates

---

## Objective
Perform a comprehensive audit to determine the true migration status by categorizing all activities across MapMyRun, Strava, and Garmin Connect, ensuring accurate assessment of MMR-to-Strava migration progress while excluding Garmin-sourced activities that bypass MMR entirely.

Categories of records to compare:
-map my run
-strava
-recent records recorded to strava via garmin, with no involvement of MMR, which therefore can be ignored in evaluating the status of migrating MMR records to strava

## Audit Categories

### 1. MapMyRun Records Analysis
**Goal**: Establish baseline of all MMR activities intended for migration

**Data Sources**:
- Local SQLite database (`Workout` table)
- Original MMR CSV export data

**Metrics to Collect**:
- Total MMR activities by date range
- Activity types distribution (run, ride, swim, hike, etc.)
- Current processing status breakdown:
  - `validation_successful`: Ready for Strava upload
  - `validation_failed`: Cannot be migrated (corrupt TCX, etc.)
  - Other statuses
- Date range coverage (earliest to latest activity)
- File size and quality statistics

**Analysis Methods** (Using Existing Tools):
```bash
# Use existing utility - no custom SQL needed
python utils/db_status_report.py

# Use existing final status summary from main.py
python main.py --dry-run --dry-run-limit 1  # Triggers status summary without uploads
```

**Additional Targeted Queries** (Only if needed):
```sql
-- Source identification from activity names (already in database)
SELECT activity_name, COUNT(*) FROM workouts 
WHERE activity_name LIKE '%Garmin%' GROUP BY activity_name;

-- Failed vs skipped analysis (key insight)
SELECT strava_status, COUNT(*) FROM workouts 
WHERE strava_status IN ('upload_failed', 'skipped_already_exists') 
GROUP BY strava_status;
```

### 2. Strava Records Analysis
**Goal**: Catalog all Strava activities to identify MMR-sourced vs. Garmin-sourced

**Data Sources**:
- Strava API (`/athlete/activities`)
- Local database Strava status tracking

**Metrics to Collect**:
- Total Strava activities in MMR date range
- Activities by source/device:
  - Garmin devices (exclude from MMR migration assessment)
  - Manual uploads (potential MMR sources)
  - Other sources
- Activity overlap analysis with MMR date/time/distance matching
- Upload timestamps vs. activity dates (detect retroactive uploads)

**Analysis Methods** (Efficient Approach):
```python
# AVOID: Querying all Strava activities (expensive, rate-limited)
# INSTEAD: Use existing duplicate detection logic selectively

# 1. Analyze existing database patterns first
failed_activities = session.query(Workout).filter(
    Workout.strava_status == 'upload_failed'
).limit(10)  # Sample for pattern analysis

# 2. Only query Strava for specific unmatched activities
# Reuse StravaUploader._is_duplicate() method which already:
# - Queries Strava by date range
# - Extracts TCX metrics for comparison
# - Identifies likely duplicates

# 3. Cache results to avoid re-querying same dates
```

**Source Identification Strategy**:
- **Garmin-sourced**: Activities with Garmin device IDs, uploaded near activity date
- **MMR-sourced**: Manual uploads, uploaded significantly after activity date
- **Ambiguous**: Require manual review or heuristic classification

### 3. Garmin Connect Exclusion Analysis
**Goal**: Identify and exclude Garmin-sourced activities from migration assessment

**Identification Criteria**:
- Upload source contains "Garmin" device identifiers
- Upload timestamp within 24 hours of activity completion
- Activity metadata indicates GPS device recording
- Cross-reference with known Garmin device models/IDs

**Exclusion Impact**:
- Calculate how many "duplicate" rejections are actually Garmin activities
- Adjust migration success metrics to exclude Garmin activities
- Identify true MMR activities that failed to migrate

### 4. Cross-Platform Matching Analysis
**Goal**: Determine which MMR activities successfully migrated vs. true failures

**Matching Criteria** (in priority order):
1. **Exact match**: Same date, duration (±30s), distance (±0.1 miles)
2. **Close match**: Same date, duration (±2 min), distance (±0.2 miles)
3. **Probable match**: Same date, similar activity type, duration (±5 min)
4. **Manual review**: Activities requiring human judgment

**Analysis Process**:
1. For each MMR activity marked as "duplicate" or "failed":
   - Search Strava activities within date range (±1 day)
   - Apply matching criteria in priority order
   - Classify as: Confirmed Match, Probable Match, No Match, Needs Review

2. For unmatched MMR activities:
   - Verify TCX file quality and upload eligibility
   - Check for edge cases (very short/long activities, unusual types)
   - Identify true migration failures requiring retry

### 5. Migration Success Calculation
**Goal**: Calculate accurate migration success rate excluding Garmin activities

**Formulas**:
```
Total MMR Activities = Count from local database
Garmin-Equivalent Activities = Strava activities identified as Garmin-sourced in MMR date range
Net MMR Activities for Migration = Total MMR - Garmin Equivalent (where overlap exists)
Successfully Migrated = Confirmed + Probable matches on Strava
Migration Success Rate = Successfully Migrated / Net MMR Activities for Migration
```

**Success Thresholds**:
- **Excellent**: 95%+ migration rate
- **Good**: 90-94% migration rate  
- **Needs Attention**: <90% migration rate

## Implementation Steps (Optimized for Efficiency)

### Phase 1: Leverage Existing Data Sources (30 min - No API Calls)
**Progress Tracking**: Console progress bars with ETA for each step

1. **Use Existing Database Reports** (10 min)
   ```
   [████████████████████████████████] 100% | Using utils/db_status_report.py
   ```
   - **EFFICIENT**: Reuse existing `utils/db_status_report.py` utility
   - **EFFICIENT**: Use `main.py --dry-run --dry-run-limit 1` for status summary
   - Generate baseline metrics without custom queries

2. **Analyze Local Database Patterns** (15 min)  
   ```
   [████████████████████████████████] 100% | Analyzing existing status patterns
   ```
   - **EFFICIENT**: Focus on `skipped_already_exists` vs `upload_failed` patterns
   - **EFFICIENT**: Use existing `activity_name` field for source identification
   - **AVOID**: Expensive Strava API calls for comprehensive catalog

3. **Review Existing Logs** (5 min)
   ```
   [████████████████████████████████] 100% | Processing upload attempt logs
   ```
   - **EFFICIENT**: Analyze existing duplicate detection logs
   - **EFFICIENT**: Review rate limit and error patterns
   - **EFFICIENT**: Use existing TCX validation results

### Phase 2: Targeted Strava Analysis (45 min - Minimal API Usage)

1. **Smart Source Classification** (20 min)
   ```
   Efficient Classification Progress:
   ├── Database activity_name analysis: [████████] Using existing data
   ├── Upload pattern analysis: [████████] Focus on failed activities  
   └── Sample validation: [████████] 10-20 activities for accuracy check
   ```
   - **EFFICIENT**: Use existing `activity_name` field patterns (e.g., "Garmin Connect")
   - **EFFICIENT**: Focus analysis on `upload_failed` activities only
   - **EFFICIENT**: Sample-based validation instead of comprehensive review

2. **Selective API Queries** (20 min)
   ```
   Targeted API Usage: [████████] 15-20 strategic queries (not 1000+)
   ```
   - **EFFICIENT**: Reuse existing `StravaUploader._is_duplicate()` logic
   - **EFFICIENT**: Query only for unmatched `upload_failed` activities
   - **EFFICIENT**: Cache responses to avoid duplicate date range queries
   - **AVOID**: Comprehensive Strava activity catalog (rate limit risk)

3. **Pattern Recognition** (5 min)
   - **EFFICIENT**: Build on existing duplicate detection patterns
   - **EFFICIENT**: Use proven matching thresholds (161m distance, 60s duration)
   - **EFFICIENT**: Leverage existing TCX parsing infrastructure

### Phase 3: Smart Cross-Platform Matching (30 min - Data-Driven)

1. **Database-First Analysis** (15 min)
   ```
   Efficient Matching Progress:
   ├── Existing duplicate patterns: [████████] From skipped_already_exists
   ├── Failed activity analysis: [████████] Focus on upload_failed only
   └── Sample validation: [████████] 10-20 strategic checks
   ```
   - **EFFICIENT**: Start with existing `skipped_already_exists` records (already matched!)
   - **EFFICIENT**: Focus matching efforts on `upload_failed` activities only
   - **EFFICIENT**: Use existing duplicate detection logic from `StravaUploader`

2. **Targeted Matching** (10 min)
   - **EFFICIENT**: Reuse existing TCX parsing (distance/duration extraction)
   - **EFFICIENT**: Apply proven matching thresholds (161m, 60s) from existing code
   - **AVOID**: Building new matching algorithms from scratch

3. **Sample-Based Validation** (5 min)
   ```
   Validation Progress: [████████] 15 strategic samples validated
   ```
   - **EFFICIENT**: Validate accuracy on small representative sample
   - **EFFICIENT**: Use existing infrastructure for confidence scoring
   - **AVOID**: Manual review of hundreds of activities

### Phase 4: Efficient Reporting (15 min - Reuse Existing Infrastructure)

1. **Extend Existing Status Summary** (10 min)
   ```
   Enhanced Reporting:
   ├── Build on main.py final status summary: [████████] Already implemented
   ├── Add Garmin exclusion calculations: [████████] Simple database query
   └── Generate action items: [████████] Focus on upload_failed records
   ```
   - **EFFICIENT**: Extend existing `print_final_status_summary()` function
   - **EFFICIENT**: Use existing database queries and utilities
   - **EFFICIENT**: Build on proven reporting infrastructure

2. **Generate Targeted Insights** (5 min)
   - **EFFICIENT**: Focus on actionable findings (retry candidates)
   - **EFFICIENT**: Use existing logging and database infrastructure
   - **EFFICIENT**: Generate specific recommendations based on patterns

**TOTAL TIME: ~2 hours (vs. 7.5 hours in comprehensive approach)**
**API CALLS: ~15-20 strategic queries (vs. 1000+ comprehensive queries)**
**EFFICIENCY GAIN: ~75% time reduction, ~95% API call reduction**

## Audit Output Specifications

### Output Formats
All audit results will be generated in multiple formats for different use cases:

1. **Console Output**: Real-time progress and summary tables with Unicode box drawing
2. **CSV Files**: Machine-readable data for spreadsheet analysis
3. **JSON API**: Structured data for programmatic access  
4. **HTML Report**: Formatted web page with interactive tables
5. **Markdown Summary**: Documentation-friendly format for archival

### File Structure
```
audit_results/
├── 2025-10-02_migration_audit/
│   ├── summary/
│   │   ├── executive_dashboard.html
│   │   ├── migration_summary.md
│   │   └── console_output.txt
│   ├── detailed_analysis/
│   │   ├── failed_migrations.csv
│   │   ├── cross_platform_matches.csv
│   │   ├── data_quality_report.csv
│   │   └── action_items.csv
│   ├── raw_data/
│   │   ├── mmr_activities.json
│   │   ├── strava_activities.json
│   │   └── garmin_exclusions.json
│   └── metadata/
│       ├── audit_config.json
│       ├── methodology.md
│       └── changelog.md
```

### Table Standardization
All tables follow consistent formatting rules:
- **Status Icons**: ✓ (success), ✗ (failure), ⚠ (warning), ℹ (info)
- **Percentages**: Rounded to 1 decimal place (95.6%)
- **Counts**: Comma-separated for readability (1,234)
- **Dates**: ISO format (2023-12-31) for consistency
- **Colors**: Green (success), Red (failure), Yellow (warning), Blue (info)

## Deliverables

### 1. Executive Summary Dashboard
**Primary Output**: Comprehensive migration status overview in tabular format

#### Master Status Table
| Metric | Count | Percentage | Status |
|--------|-------|------------|--------|
| Total MMR Activities | 1,234 | 100.0% | ✓ Complete |
| Successfully Migrated | 1,180 | 95.6% | ✓ Excellent |
| Failed Migration | 54 | 4.4% | ⚠ Needs Review |
| Garmin Exclusions | 89 | 7.2% | ℹ Informational |
| Net Migration Rate | 95.6% | - | ✓ Target Met |

#### Activity Source Breakdown
| Source | Total Activities | Date Range | Upload Pattern | Migration Relevant |
|--------|------------------|------------|----------------|-------------------|
| MapMyRun Original | 1,234 | 2018-2023 | Historical Export | ✓ Yes |
| Strava Direct (MMR-sourced) | 1,180 | 2018-2023 | Manual Upload | ✓ Matched |
| Garmin Connect | 89 | 2022-2023 | Auto-sync | ✗ Excluded |
| Strava Other Sources | 45 | 2018-2023 | Various | ℹ Under Review |

#### Activity Type Distribution
| Activity Type | MMR Count | Strava Matched | Success Rate | Failed Count |
|---------------|-----------|----------------|--------------|--------------|
| Running | 856 | 820 | 95.8% | 36 |
| Cycling | 234 | 228 | 97.4% | 6 |
| Walking | 89 | 85 | 95.5% | 4 |
| Hiking | 34 | 32 | 94.1% | 2 |
| Swimming | 21 | 15 | 71.4% | 6 |

### 2. Detailed Analysis Reports

#### Failed Migration Analysis Table
| MMR ID | Date | Activity Type | Duration | Distance | Failure Reason | Retry Eligible | Action Required |
|--------|------|---------------|----------|----------|----------------|----------------|-----------------|
| MMR_001 | 2019-03-15 | Running | 35:42 | 4.2 mi | TCX Validation Failed | ✗ No | Archive |
| MMR_002 | 2020-07-22 | Cycling | 1:23:15 | 23.1 mi | Strava API Error | ✓ Yes | Retry Upload |
| MMR_003 | 2021-11-08 | Swimming | 42:30 | 1500m | No GPS Data | ✗ No | Manual Entry |

#### Cross-Platform Matching Results
| Match Type | Count | Confidence | Manual Review Required |
|------------|-------|------------|----------------------|
| Exact Match | 987 | High (95-100%) | ✗ No |
| Close Match | 156 | Medium (80-94%) | ⚠ Recommended |
| Probable Match | 37 | Low (60-79%) | ✓ Yes |
| No Match Found | 54 | N/A | ✓ Yes |

#### Data Quality Assessment
| Quality Metric | MMR Source | Strava Target | Match Rate | Quality Score |
|----------------|------------|---------------|------------|---------------|
| Date Accuracy | 100% | 99.8% | 99.8% | A+ |
| Duration Data | 98.5% | 100% | 98.5% | A |
| Distance Data | 95.2% | 99.1% | 94.5% | A- |
| GPS Coordinates | 87.3% | 91.2% | 86.8% | B+ |
| Activity Type | 100% | 98.9% | 98.9% | A |

### 3. Actionable Insights Tables

#### Immediate Action Items
| Priority | Action | Count | Estimated Time | Expected Success Rate |
|----------|--------|-------|----------------|----------------------|
| High | Retry API Failed Uploads | 18 | 2 hours | 90% |
| Medium | Manual Review Ambiguous Matches | 37 | 4 hours | 75% |
| Low | Investigate No-GPS Swimming Activities | 6 | 1 hour | 25% |

#### Exclusion Summary
| Exclusion Reason | Count | Percentage of Total | Impact on Success Rate |
|------------------|-------|---------------------|----------------------|
| Garmin Auto-Sync Duplicates | 89 | 7.2% | +2.1% improvement |
| Corrupt TCX Files | 12 | 1.0% | Unavoidable |
| Invalid Activity Types | 3 | 0.2% | Negligible |

### 4. Technical Implementation Outputs

#### Database Status Summary
```sql
-- Generated report query results in tabular format:
CREATE VIEW audit_summary AS 
SELECT 
    status_category,
    COUNT(*) as record_count,
    ROUND(COUNT(*) * 100.0 / total.count, 2) as percentage
FROM (
    SELECT 
        CASE 
            WHEN strava_upload_status = 'success' THEN 'Successfully Migrated'
            WHEN strava_upload_status = 'duplicate' AND garmin_equivalent = 1 THEN 'Garmin Exclusion'
            WHEN strava_upload_status = 'failed' THEN 'Migration Failed'
            ELSE 'Pending Review'
        END as status_category
    FROM workouts w
    CROSS JOIN (SELECT COUNT(*) as count FROM workouts) total
);
```

#### API Query Results Format
```json
{
  "audit_timestamp": "2025-10-02T14:30:00Z",
  "summary_tables": {
    "master_status": [...],
    "source_breakdown": [...],
    "activity_types": [...],
    "failed_analysis": [...],
    "match_results": [...],
    "data_quality": [...],
    "action_items": [...],
    "exclusions": [...]
  },
  "metadata": {
    "total_mmr_activities": 1234,
    "audit_date_range": "2018-01-01 to 2023-12-31",
    "confidence_threshold": 0.80,
    "exclusion_criteria": ["garmin_device", "upload_within_24h"]
  }
}
```

### 5. Visual Summary Outputs

#### Console Output Format
```
╔═══════════════════════════════════════════════════════════════╗
║                  MMR TO STRAVA MIGRATION AUDIT               ║
╠═══════════════════════════════════════════════════════════════╣
║ Total MMR Activities:     1,234                               ║
║ Successfully Migrated:    1,180 (95.6%) ✓                    ║
║ Migration Failures:          54 (4.4%)  ⚠                    ║
║ Garmin Exclusions:           89 (7.2%)  ℹ                    ║
║                                                               ║
║ NET MIGRATION SUCCESS RATE: 95.6% (EXCELLENT) ✓              ║
╚═══════════════════════════════════════════════════════════════╝

┌─────────────────┬─────────┬─────────┬────────────┬─────────────┐
│ Activity Type   │ MMR     │ Strava  │ Success %  │ Failed      │
├─────────────────┼─────────┼─────────┼────────────┼─────────────┤
│ Running         │     856 │     820 │      95.8% │          36 │
│ Cycling         │     234 │     228 │      97.4% │           6 │
│ Walking         │      89 │      85 │      95.5% │           4 │
│ Hiking          │      34 │      32 │      94.1% │           2 │
│ Swimming        │      21 │      15 │      71.4% │           6 │
└─────────────────┴─────────┴─────────┴────────────┴─────────────┘
```

## Risk Mitigation

- **False Positives**: Conservative matching criteria to avoid over-counting successes
- **Data Quality**: Validate sample results manually before full automation
- **API Limits**: Implement proper rate limiting and caching for Strava queries
- **Date Ambiguity**: Handle timezone differences and date formatting consistently
- **Edge Cases**: Document and handle unusual activity patterns (multi-day, very short, etc.)

## Success Criteria

- Clear identification of Garmin vs. MMR sourced activities on Strava
- Accurate migration success rate calculation (target: 95%+ for MMR-specific activities)
- Actionable list of true migration failures for remediation
- Confidence in migration completion status for project closure
