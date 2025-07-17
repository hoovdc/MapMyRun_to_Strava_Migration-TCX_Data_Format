import logging
import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

class Workout(Base):
    """Database model for a workout."""
    __tablename__ = 'workouts'

    id = Column(Integer, primary_key=True)
    workout_id = Column(Integer, unique=True, nullable=False)
    activity_type = Column(String)
    workout_date = Column(DateTime)
    download_path = Column(String, nullable=True)
    # Statuses: pending, downloaded, validated, failed, uploaded
    status = Column(String, default='pending', nullable=False)

    def __repr__(self):
        return f"<Workout(workout_id='{self.workout_id}', status='{self.status}')>"

class DatabaseManager:
    """Handles all database interactions."""
    def __init__(self, db_path='data/progress_tracking_data/migration_progress.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        """Provides a new session."""
        return self.Session() 