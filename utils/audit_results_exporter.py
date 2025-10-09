#!/usr/bin/env python3
"""
Audit Results Exporter - Generates CSV reports for easy inspection
"""
import sys
import os
import logging
import csv
from datetime import datetime
from sqlalchemy import func

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database_manager import DatabaseManager, Workout
from utils.logger import setup_logger

def export_audit_results():
    """
    Export audit results to CSV files for easy inspection
    """
    setup_logger(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"audit_results/{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 1. Master Status Summary CSV
        export_master_status(session, f"{output_dir}/master_status.csv")
        
        # 2. Failed Activities Detail CSV
        export_failed_activities(session, f"{output_dir}/failed_activities.csv")
        
        # 3. Garmin Exclusions CSV
        export_garmin_exclusions(session, f"{output_dir}/garmin_exclusions.csv")
        
        # 4. Activity Type Breakdown CSV
        export_activity_breakdown(session, f"{output_dir}/activity_breakdown.csv")
        
        # 5. Action Items CSV
        export_action_items(session, f"{output_dir}/action_items.csv")
        
        logger.info(f"Audit results exported to: {output_dir}")
        print(f"\n📊 Audit Results Available:")
        print(f"   📁 Directory: {output_dir}")
        print(f"   📋 Files: master_status.csv, failed_activities.csv, garmin_exclusions.csv")
        print(f"   🔍 Open in Excel/LibreOffice for easy inspection")
        
    except Exception as e:
        logger.error(f"Error exporting audit results: {e}")
    finally:
        session.close()

def export_master_status(session, filepath):
    """Export master status summary"""
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Metric', 'Count', 'Percentage', 'Status'])
        
        # Get total count
        total = session.query(Workout).count()
        
        # MMR Status breakdown
        mmr_counts = session.query(
            Workout.mmr_status, func.count(Workout.mmr_status)
        ).group_by(Workout.mmr_status).all()
        
        for status, count in mmr_counts:
            pct = round(count * 100.0 / total, 1) if total > 0 else 0
            writer.writerow([f'MMR {status}', count, f'{pct}%', '✓' if status == 'validation_successful' else '⚠'])
        
        # Strava Status breakdown
        strava_counts = session.query(
            Workout.strava_status, func.count(Workout.strava_status)
        ).group_by(Workout.strava_status).all()
        
        for status, count in strava_counts:
            pct = round(count * 100.0 / total, 1) if total > 0 else 0
            icon = '✓' if status in ['upload_successful', 'skipped_already_exists'] else '⚠'
            writer.writerow([f'Strava {status}', count, f'{pct}%', icon])

def export_failed_activities(session, filepath):
    """Export detailed failed activities"""
    failed_activities = session.query(Workout).filter(
        Workout.strava_status == 'upload_failed'
    ).all()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Workout_ID', 'Date', 'Activity_Type', 'Activity_Name', 'MMR_Status', 'Strava_Status', 'Retry_Eligible'])
        
        for workout in failed_activities:
            retry_eligible = 'Yes' if workout.mmr_status == 'validation_successful' else 'No'
            writer.writerow([
                workout.workout_id,
                workout.workout_date.strftime('%Y-%m-%d') if workout.workout_date else 'N/A',
                workout.activity_type or 'Unknown',
                workout.activity_name or 'N/A',
                workout.mmr_status,
                workout.strava_status,
                retry_eligible
            ])

def export_garmin_exclusions(session, filepath):
    """Export potential Garmin exclusions"""
    garmin_activities = session.query(Workout).filter(
        Workout.activity_name.like('%Garmin%')
    ).all()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Workout_ID', 'Date', 'Activity_Name', 'Strava_Status', 'Exclusion_Reason'])
        
        for workout in garmin_activities:
            exclusion_reason = 'Garmin Connect Source' if 'Garmin' in (workout.activity_name or '') else 'Review Needed'
            writer.writerow([
                workout.workout_id,
                workout.workout_date.strftime('%Y-%m-%d') if workout.workout_date else 'N/A',
                workout.activity_name or 'N/A',
                workout.strava_status,
                exclusion_reason
            ])

def export_activity_breakdown(session, filepath):
    """Export activity type breakdown with run priority focus"""
    type_counts = session.query(
        Workout.activity_type, 
        Workout.strava_status,
        func.count().label('count')
    ).group_by(Workout.activity_type, Workout.strava_status).all()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Activity_Type', 'Strava_Status', 'Count', 'Priority', 'Migration_Phase'])
        
        for activity_type, strava_status, count in type_counts:
            # Prioritize runs
            if activity_type and 'run' in activity_type.lower():
                priority = 'HIGH'
                phase = 'Phase 1 (Current)'
            else:
                priority = 'LOW'
                phase = 'Phase 2 (Future)'
            
            writer.writerow([activity_type or 'Unknown', strava_status, count, priority, phase])

def export_action_items(session, filepath):
    """Export prioritized action items"""
    # High priority: validation_successful but upload_failed
    high_priority = session.query(Workout).filter(
        Workout.mmr_status == 'validation_successful',
        Workout.strava_status == 'upload_failed'
    ).all()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Priority', 'Workout_ID', 'Date', 'Activity_Type', 'Action_Required', 'Estimated_Success'])
        
        for workout in high_priority:
            writer.writerow([
                'HIGH',
                workout.workout_id,
                workout.workout_date.strftime('%Y-%m-%d') if workout.workout_date else 'N/A',
                workout.activity_type or 'Unknown',
                'Retry Upload',
                '90%'
            ])

if __name__ == "__main__":
    export_audit_results()
