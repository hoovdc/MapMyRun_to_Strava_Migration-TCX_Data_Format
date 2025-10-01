# MapMyRun to Strava Migration: Record Status Audit Plan

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

### Phase 1: Data Collection (Automated)
1. Export comprehensive MMR database statistics
2. Query Strava API for all activities in MMR date range
3. Analyze Strava activity sources and upload patterns
4. Generate raw data reports for each category

### Phase 2: Source Classification (Semi-Automated)
1. Apply Garmin identification heuristics
2. Flag ambiguous activities for manual review
3. Create exclusion lists and inclusion lists
4. Validate classification accuracy on sample data

### Phase 3: Cross-Platform Matching (Automated + Manual)
1. Run automated matching algorithms
2. Generate match confidence scores
3. Create manual review queue for low-confidence matches
4. Validate matching accuracy on known samples

### Phase 4: Final Assessment (Reporting)
1. Calculate adjusted migration success rates
2. Identify specific failed activities requiring attention
3. Generate actionable recommendations
4. Create executive summary with key findings

## Deliverables

1. **Raw Data Reports**:
   - MMR activity inventory with statistics
   - Strava activity catalog with source classification
   - Garmin activity exclusion list

2. **Matching Analysis**:
   - MMR-to-Strava activity matching results
   - Confidence scores and manual review queue
   - Unmatched activity analysis

3. **Executive Summary**:
   - Adjusted migration success rate
   - Key findings and recommendations
   - Action items for remaining failures

4. **Technical Documentation**:
   - Audit methodology and assumptions
   - Data quality assessment
   - Reproducible analysis scripts

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
