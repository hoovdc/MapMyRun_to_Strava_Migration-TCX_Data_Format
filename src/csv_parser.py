import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

class WorkoutInventory:
    """Parses the MapMyRun CSV export to create a workout inventory."""
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        try:
            self.df = pd.read_csv(self.csv_path)
            # Sanitize column names by stripping whitespace
            self.df.columns = self.df.columns.str.strip()
            logger.info(f"Successfully loaded {len(self.df)} workouts from {self.csv_path}")
        except FileNotFoundError:
            logger.error(f"CSV file not found at {self.csv_path}")
            self.df = pd.DataFrame()

    def extract_workouts(self) -> list[dict]:
        """
        Extracts workout details from the CSV data.

        Returns:
            A list of dictionaries, each representing a workout.
        """
        if self.df.empty:
            return []

        workouts = []
        for _, row in self.df.iterrows():
            try:
                workout_id = self._extract_id_from_link(row['Link'])
                if workout_id:
                    workouts.append({
                        'workout_id': workout_id,
                        'activity_name': row.get('Activity Name'),
                        'notes': row.get('Notes'),
                        'activity_type': row.get('Activity Type'),
                        'workout_date': self._parse_date(row.get('Workout Date'))
                    })
            except Exception as e:
                logger.warning(f"Could not process row: {row}. Error: {e}")
        
        return workouts

    def _extract_id_from_link(self, link: str) -> int | None:
        """Extracts the numerical workout ID from a URL string."""
        if not isinstance(link, str) or not link:
            return None
        try:
            return int(link.strip().split('/')[-1])
        except (ValueError, IndexError):
            logger.warning(f"Could not extract workout ID from link: {link}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime | None:
        """Parses common date string formats into a datetime object."""
        if not isinstance(date_str, str) or not date_str:
            return None
        
        # Pre-process the string to handle the non-standard "Sept." abbreviation
        processed_date_str = date_str.replace('Sept.', 'Sep.')

        # List of possible date formats to try
        formats_to_try = [
            '%B %d, %Y',  # e.g., "July 15, 2025"
            '%b. %d, %Y'  # e.g., "Sep. 28, 2024"
        ]

        for fmt in formats_to_try:
            try:
                return datetime.strptime(processed_date_str, fmt)
            except ValueError:
                continue
        
        # If all formats fail, log a warning
        logger.warning(f"Could not parse date with any known format: {date_str}")
        return None 