#!/usr/bin/env python3
"""
Test script to verify the duplicate detection fix works.
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database_manager import DatabaseManager, Workout
from strava_uploader import StravaUploader
from strava_auth import StravaAuthenticator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_duplicate_detection():
    """Test the enhanced duplicate detection on a known duplicate workout."""
    
    # Get the known duplicate workout
    db = DatabaseManager()
    session = db.get_session()
    
    workout = session.query(Workout).filter(Workout.workout_id == '8609714873').first()
    if not workout:
        print("❌ Test workout 8609714873 not found in database")
        return
    
    print(f"🧪 Testing duplicate detection on workout {workout.workout_id}")
    print(f"   Current status: {workout.strava_status}")
    print(f"   Activity name: {workout.activity_name}")
    
    # Initialize Strava components
    try:
        client_id = os.getenv('STRAVA_CLIENT_ID')
        client_secret = os.getenv('STRAVA_CLIENT_SECRET')
        
        auth = StravaAuthenticator(client_id, client_secret)
        client = auth.get_authenticated_client()
        uploader = StravaUploader(client, db, dry_run=False)
        
        # Test the upload (should detect as duplicate)
        print("🚀 Attempting upload...")
        uploader.upload_activity(workout)
        
        # Check final status
        session.refresh(workout)
        print(f"✅ Final status: {workout.strava_status}")
        
        if workout.strava_status == 'skipped_already_exists':
            print("🎉 SUCCESS: Duplicate detection is working!")
        elif workout.strava_status == 'upload_failed':
            print("⚠️  Still marked as failed - duplicate detection may not be working")
        else:
            print(f"❓ Unexpected status: {workout.strava_status}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_duplicate_detection()
