#!/usr/bin/env python3
"""
Database Monitor - Quick SQLite inspection while app runs
"""
import sys
import os
import sqlite3
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def quick_status():
    """Quick status check without SQLAlchemy"""
    db_path = os.path.join(project_root, 'data', 'progress_tracking_data', 'migration_progress.db')
    
    if not os.path.exists(db_path):
        print("❌ Database not found")
        return
    
    try:
        # Read-only connection
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        
        print(f"📊 Database Status - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)
        
        # Status counts
        cursor.execute("""
            SELECT strava_status, COUNT(*) as count 
            FROM workouts 
            GROUP BY strava_status 
            ORDER BY count DESC
        """)
        
        total = 0
        for status, count in cursor.fetchall():
            print(f"{status:25}: {count:>6}")
            total += count
        
        print("-" * 50)
        print(f"{'Total':25}: {total:>6}")
        
        # Recent activity (last 10 changes)
        cursor.execute("""
            SELECT workout_id, activity_type, strava_status, workout_date
            FROM workouts 
            WHERE strava_status IN ('upload_successful', 'skipped_already_exists', 'upload_failed')
            ORDER BY rowid DESC 
            LIMIT 10
        """)
        
        print("\n🕒 Recent Status Changes:")
        print("-" * 70)
        for workout_id, activity_type, status, date in cursor.fetchall():
            date_str = date[:10] if date else 'N/A'
            print(f"{workout_id:>8} | {activity_type:>10} | {status:20} | {date_str}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def interactive_query():
    """Interactive SQL query mode"""
    db_path = os.path.join(project_root, 'data', 'progress_tracking_data', 'migration_progress.db')
    
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        
        print("🔍 Interactive Query Mode (Read-Only)")
        print("Type 'exit' to quit, 'status' for quick status")
        print("Example: SELECT COUNT(*) FROM workouts WHERE strava_status = 'upload_failed';")
        print("-" * 70)
        
        while True:
            query = input("SQL> ").strip()
            
            if query.lower() == 'exit':
                break
            elif query.lower() == 'status':
                quick_status()
                continue
            elif not query:
                continue
            
            try:
                cursor.execute(query)
                results = cursor.fetchall()
                
                if results:
                    # Print column headers if available
                    if cursor.description:
                        headers = [desc[0] for desc in cursor.description]
                        print(" | ".join(f"{h:>15}" for h in headers))
                        print("-" * (len(headers) * 18))
                    
                    # Print results
                    for row in results:
                        print(" | ".join(f"{str(val):>15}" for val in row))
                else:
                    print("No results")
                    
            except Exception as e:
                print(f"❌ Query error: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        interactive_query()
    else:
        quick_status()
