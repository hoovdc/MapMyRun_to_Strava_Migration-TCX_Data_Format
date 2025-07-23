import logging
import os
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

# --- Schema Version ---
# Version 1: Initial schema.
# Version 2: Added strava_activity_id.
# Version 3: Added activity_name and notes.
SCHEMA_VERSION = 3

Base = declarative_base()

class Workout(Base):
    """Database model for a workout."""
    __tablename__ = 'workouts'

    id = Column(Integer, primary_key=True)
    workout_id = Column(Integer, unique=True, nullable=False)
    activity_name = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    activity_type = Column(String)
    workout_date = Column(DateTime)
    download_path = Column(String, nullable=True)
    mmr_status = Column(Enum('pending_download', 'download_failed', 'validation_successful', 'validation_failed'), default='pending_download', nullable=False)
    strava_status = Column(Enum('pending_upload', 'upload_successful', 'upload_failed', 'skipped_already_exists', 'upload_failed_file_not_found'), default='pending_upload', nullable=False)
    strava_activity_id = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Workout(workout_id='{self.workout_id}', mmr_status='{self.mmr_status}', strava_status='{self.strava_status}')>"

class DatabaseManager:
    """Handles all database interactions, including schema versioning and automatic rebuilds."""
    def __init__(self, db_path='data/progress_tracking_data/migration_progress.db'):
        self.db_path = db_path
        self.was_rebuilt = False
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self._check_schema_version()

        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        
        if self.was_rebuilt:
            self._stamp_schema_version()
            
        self.Session = sessionmaker(bind=self.engine)

    def _get_db_connection(self):
        """Creates a direct sqlite3 connection to check metadata."""
        return sqlite3.connect(self.db_path)

    def _check_schema_version(self):
        """Checks the on-disk DB schema version and triggers a rebuild if outdated."""
        if not os.path.exists(self.db_path):
            logger.info("Database file not found. A new one will be created.")
            self.was_rebuilt = True
            return

        try:
            con = self._get_db_connection()
            cursor = con.cursor()
            cursor.execute("PRAGMA table_info(schema_version)")
            if not cursor.fetchone(): # table doesn't exist
                raise sqlite3.OperationalError
            
            cursor.execute("SELECT version FROM schema_version")
            db_version = cursor.fetchone()[0]

            if db_version < SCHEMA_VERSION:
                logger.warning(f"Database schema is outdated (DB version: {db_version}, Code version: {SCHEMA_VERSION}). Triggering automatic rebuild.")
                self.was_rebuilt = True
            else:
                logger.info("Database schema is up-to-date.")

        except sqlite3.OperationalError:
            logger.warning("Could not determine database schema version. Assuming outdated and triggering rebuild.")
            self.was_rebuilt = True
        finally:
            if 'con' in locals() and con:
                con.close()
        
        if self.was_rebuilt:
            if 'con' in locals() and con:
                con.close()
            os.remove(self.db_path)
            
    def _stamp_schema_version(self):
        """Writes the current schema version to the database."""
        try:
            con = self._get_db_connection()
            cursor = con.cursor()
            cursor.execute("CREATE TABLE schema_version (version INTEGER)")
            cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            con.commit()
            logger.info(f"Stamped database with schema version {SCHEMA_VERSION}.")
        finally:
            if con:
                con.close()

    def get_session(self):
        """Provides a new session."""
        return self.Session() 