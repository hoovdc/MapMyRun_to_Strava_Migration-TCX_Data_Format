#!/usr/bin/env python3
"""
Live Audit Dashboard - Real-time console display of migration status
"""
import sys
import os
import time
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database_manager import DatabaseManager, Workout
from sqlalchemy import func

def display_live_dashboard():
    """Display live migration status dashboard"""
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
            
            print("╔═══════════════════════════════════════════════════════════════╗")
            print("║                  LIVE MIGRATION AUDIT DASHBOARD              ║")
            print(f"║                  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                ║")
            print("╠═══════════════════════════════════════════════════════════════╣")
            
            # Get counts
            total = session.query(Workout).count()
            successful = session.query(Workout).filter(Workout.strava_status == 'upload_successful').count()
            skipped = session.query(Workout).filter(Workout.strava_status == 'skipped_already_exists').count()
            failed = session.query(Workout).filter(Workout.strava_status == 'upload_failed').count()
            pending = session.query(Workout).filter(Workout.strava_status == 'pending_upload').count()
            
            confirmed_on_strava = successful + skipped
            success_rate = (confirmed_on_strava / total * 100) if total > 0 else 0
            
            print(f"║ Total Activities:        {total:>6}                               ║")
            print(f"║ Confirmed on Strava:     {confirmed_on_strava:>6} ({success_rate:>5.1f}%)                    ║")
            print(f"║   ├─ Upload Successful:  {successful:>6}                               ║")
            print(f"║   └─ Skipped (Duplicate):{skipped:>6}                               ║")
            print(f"║ Pending Upload:          {pending:>6}                               ║")
            print(f"║ Upload Failed:           {failed:>6}                               ║")
            print("╠═══════════════════════════════════════════════════════════════╣")
            
            # Success indicator
            if success_rate >= 95:
                print("║ STATUS: 🎉 EXCELLENT (95%+ confirmed)                        ║")
            elif success_rate >= 90:
                print("║ STATUS: ✅ GOOD (90%+ confirmed)                             ║")
            else:
                print("║ STATUS: ⚠️  IN PROGRESS (More confirmations needed)          ║")
            
            print("╚═══════════════════════════════════════════════════════════════╝")
            print("\nPress Ctrl+C to exit, or wait 30 seconds for refresh...")
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
    finally:
        session.close()

if __name__ == "__main__":
    display_live_dashboard()
