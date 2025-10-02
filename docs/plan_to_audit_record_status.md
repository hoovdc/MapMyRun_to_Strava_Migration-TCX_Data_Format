# MapMyRun to Strava Migration: Record Status Audit Plan

## Quick Reference

| **Audit Scope** | **Time Estimate** | **Primary Output** | **Success Target** |
|-----------------|-------------------|--------------------|--------------------|
| 1,234 MMR Activities | 7.5 hours total | Executive Dashboard | 95%+ migration rate |

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

**Analysis Methods**:
```sql
-- Total activities by status
SELECT mmr_status, COUNT(*) as count, 
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM workouts), 2) as percentage
FROM workouts GROUP BY mmr_status;

-- Activity types distribution
SELECT activity_type, COUNT(*) as count FROM workouts GROUP BY activity_type;

-- Date range analysis
SELECT MIN(workout_date) as earliest, MAX(workout_date) as latest,
       COUNT(DISTINCT DATE(workout_date)) as unique_days
FROM workouts;
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

**Analysis Methods**:
```python
# Query Strava for activities in MMR date range
# Group by upload_id_str patterns to identify sources
# Cross-reference with MMR activities by date/time/distance
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

## Implementation Steps

### Phase 1: Data Collection (Automated) - 2 hours
**Progress Tracking**: Console progress bars with ETA for each step

1. **Export MMR Database Statistics** (30 min)
   ```
   [████████████████████████████████] 100% | Analyzing 1,234 MMR activities
   ```
   - Generate activity counts by type, date range, status
   - Export validation results and file quality metrics
   - Create baseline metrics table

2. **Query Strava API Activities** (45 min)  
   ```
   [██████████████████░░░░░░░░░░░░░░] 60% | Processing 2018-2020 activities...
   ```
   - Paginated API calls with rate limiting (200 activities/page)
   - Collect activity metadata, upload sources, timestamps
   - Build comprehensive Strava activity catalog

3. **Analyze Upload Sources** (30 min)
   ```
   [████████████████████████████████] 100% | Classified 1,456 Strava activities
   ```
   - Pattern matching for Garmin device identifiers
   - Upload timing analysis (auto-sync vs manual)
   - Generate source classification table

4. **Create Data Reports** (15 min)
   - Export raw data in CSV and JSON formats
   - Generate summary statistics tables
   - Validate data completeness and quality

### Phase 2: Source Classification (Semi-Automated) - 1.5 hours

1. **Apply Garmin Detection Heuristics** (30 min)
   ```
   Garmin Classification Progress:
   ├── Device ID patterns: [████████] 145 activities identified
   ├── Upload timing analysis: [████████] 89 auto-sync detected  
   └── GPS metadata check: [████████] 134 device-recorded activities
   ```
   - Pattern match against known Garmin device strings
   - Analyze upload-to-activity time deltas (<24 hours = auto-sync)
   - Cross-reference GPS metadata for device signatures

2. **Generate Review Queues** (30 min)
   ```
   Manual Review Queue: 37 ambiguous activities requiring classification
   ```
   - Flag low-confidence classifications
   - Create prioritized review list by activity importance
   - Generate classification confidence scores

3. **Create Exclusion Lists** (20 min)
   - Export confirmed Garmin activities for exclusion
   - Document classification criteria and edge cases
   - Validate sample accuracy (>95% target)

4. **Quality Assurance** (10 min)
   - Sample validation on 50 known activities
   - Adjust heuristics based on false positive/negative rates
   - Document final classification accuracy

### Phase 3: Cross-Platform Matching (Automated + Manual) - 3 hours

1. **Automated Matching Engine** (1.5 hours)
   ```
   Matching Progress by Criteria:
   ├── Exact matches (±30s, ±0.1mi): [████████] 987 found (80.0%)
   ├── Close matches (±2min, ±0.2mi): [████████] 156 found (12.6%) 
   ├── Probable matches (±5min): [██████░░] 37 found (3.0%)
   └── No matches found: [████████] 54 activities (4.4%)
   ```
   - Fuzzy matching algorithm with configurable thresholds
   - Confidence scoring based on multiple criteria
   - Duplicate detection within same-source activities  

2. **Generate Match Reports** (30 min)
   - Export match results with confidence scores
   - Create manual review queue for low-confidence matches
   - Flag potential duplicates within Strava

3. **Manual Review Process** (45 min)
   ```
   Manual Review Progress: [██████████████░░░░░░] 73% (27/37 activities reviewed)
   ```
   - Structured review process with standardized criteria
   - Accept/reject/modify automated match suggestions
   - Document review decisions and reasoning

4. **Validation & Quality Check** (15 min)
   - Cross-validate sample of automated matches
   - Verify manual review consistency
   - Generate final matching accuracy report

### Phase 4: Final Assessment & Reporting (1 hour)

1. **Calculate Migration Metrics** (20 min)
   ```
   Computing Final Statistics:
   ├── Net migration rate: [████████] 95.6% (1,180/1,234 eligible)
   ├── Success by activity type: [████████] 5 categories analyzed
   └── Action items identified: [████████] 54 activities need attention
   ```
   - Apply exclusion rules and calculate adjusted success rates
   - Generate activity-type breakdowns and trend analysis
   - Identify patterns in failed migrations

2. **Generate Executive Summary** (25 min)
   - Create all formatted tables and visual outputs
   - Generate actionable recommendations with priorities
   - Export summary in multiple formats (console, JSON, CSV)

3. **Create Action Plans** (10 min)
   - Prioritize failed activities by retry potential
   - Estimate time/effort for remediation activities
   - Generate specific next-step recommendations

4. **Final Documentation** (5 min)
   - Archive all analysis data and intermediate results
   - Document methodology and assumptions for future reference
   - Generate reproducible analysis scripts

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
