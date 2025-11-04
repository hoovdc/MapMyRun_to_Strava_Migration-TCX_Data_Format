import logging
from datetime import datetime, timedelta
from sqlalchemy import func

# pylint: disable=not-callable
# SQLAlchemy func calls are dynamic and confuse static analyzers

logger = logging.getLogger(__name__)

class DateRangeAnalyzer:
    """Handles comprehensive date range analysis for workout data."""
    
    def __init__(self, session, workout_model):
        self.session = session
        self.Workout = workout_model
    
    def generate_analysis(self):
        """Generate and print complete date range analysis."""
        print("--- Date Range Analysis ---")
        
        date_stats = self._get_basic_stats()
        if not date_stats['earliest']:
            print("No workout dates found in database.")
            print()
            return
            
        self._print_basic_metrics(date_stats)
        self._print_yearly_distribution()
        self._print_recent_activity(date_stats['latest'])
        self._print_quality_indicators(date_stats)
        
    def _get_basic_stats(self):
        """Get basic date statistics from database."""
        result = self.session.query(
            func.min(self.Workout.workout_date).label('earliest'),
            func.max(self.Workout.workout_date).label('latest'),
            func.count(self.Workout.workout_date).label('total_with_dates'),
            func.count(self.Workout.id).label('total_records')
        ).first()
        
        return {
            'earliest': result.earliest,
            'latest': result.latest,
            'total_with_dates': result.total_with_dates,
            'total_records': result.total_records
        }
    
    def _print_basic_metrics(self, stats):
        """Print basic date range metrics."""
        earliest, latest = stats['earliest'], stats['latest']
        total_days = (latest - earliest).days + 1
        records_with_dates = stats['total_with_dates']
        total_records = stats['total_records']
        
        print(f"{'Metric':<25} | {'Value':<15}")
        print("-" * 42)
        print(f"{'Earliest Activity':<25} | {earliest.strftime('%Y-%m-%d'):<15}")
        print(f"{'Latest Activity':<25} | {latest.strftime('%Y-%m-%d'):<15}")
        print(f"{'Total Date Range':<25} | {total_days:,} days")
        print(f"{'Records with Dates':<25} | {records_with_dates:,}/{total_records:,}")
        print(f"{'Coverage Period':<25} | {(latest.year - earliest.year + 1)} years")
        print("-" * 42)
    
    def _print_yearly_distribution(self):
        """Print activity distribution by year."""
        activities_by_year = self.session.query(
            func.strftime('%Y', self.Workout.workout_date).label('year'),
            func.count(self.Workout.id).label('count')
        ).filter(self.Workout.workout_date.isnot(None))\
         .group_by(func.strftime('%Y', self.Workout.workout_date))\
         .order_by('year').all()
        
        if not activities_by_year:
            return
            
        print("\n--- Activity Distribution by Year ---")
        print("Year     | Activities   | Avg/Month ")
        print("-" * 32)
        
        for year, count in activities_by_year:
            avg_per_month = round(count / 12, 1)
            print(f"{year:<8} | {count:<12,} | {avg_per_month:<10}")
        print("-" * 32)
    
    def _print_recent_activity(self, latest_date):
        """Print recent activity analysis (last 90 days)."""
        cutoff_date = latest_date - timedelta(days=90)
        recent_count = self.session.query(func.count(self.Workout.id)).filter(
            self.Workout.workout_date >= cutoff_date
        ).scalar()
        
        print("\n--- Recent Activity Summary ---")
        print(f"{'Metric':<25} | {'Value':<15}")
        print("-" * 42)
        print(f"{'Last 90 Days':<25} | {recent_count:,} activities")
        print(f"{'Average per Week':<25} | {round(recent_count / 13, 1)}")
        print(f"{'Days Since Latest':<25} | {(datetime.now().date() - latest_date.date()).days} days")
        print("-" * 42)
    
    def _print_quality_indicators(self, stats):
        """Print data quality indicators."""
        print("\n--- Data Quality Indicators ---")
        
        # Check for date gaps (periods >30 days with no activities)
        gap_count = self._count_large_gaps()
        
        # Activity consistency score (activities per month average)  
        total_days = (stats['latest'] - stats['earliest']).days + 1
        consistency_score = round((stats['total_with_dates'] / (total_days / 30.44)), 1)  # 30.44 avg days per month
        completeness = round(stats['total_with_dates']/stats['total_records']*100, 1)
        
        print(f"{'Metric':<25} | {'Value':<15}")
        print("-" * 42)
        print(f"{'Large Gaps (>30 days)':<25} | {gap_count}")
        print(f"{'Avg Activities/Month':<25} | {consistency_score}")
        print(f"{'Date Completeness':<25} | {completeness}%")
        print("-" * 42)
        print()
    
    def _count_large_gaps(self):
        """Count periods with >30 day gaps between activities."""
        try:
            gaps_query = """
            WITH date_gaps AS (
                SELECT 
                    workout_date,
                    LAG(workout_date) OVER (ORDER BY workout_date) as prev_date,
                    julianday(workout_date) - julianday(LAG(workout_date) OVER (ORDER BY workout_date)) as gap_days
                FROM workouts 
                WHERE workout_date IS NOT NULL
                ORDER BY workout_date
            )
            SELECT COUNT(*) as gap_count
            FROM date_gaps 
            WHERE gap_days > 30
            """
            
            result = self.session.execute(gaps_query).fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.warning("Could not calculate gaps: %s", e)
            return "N/A"
