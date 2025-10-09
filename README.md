# MapMyRun to Strava Migration Tool

This is a Python-based automation tool for migrating fitness workout data from MapMyRun to Strava. It uses a session cookie for reliable TCX file downloads, bypassing the need for complex UI automation, and then handles validation and bulk uploads to Strava.

**Note**: This is an open-source tool designed for personal fitness data migration projects.

For detailed project planning and history, see [docs/mapmyrun-to-strava-migration-plan.md](docs/mapmyrun-to-strava-migration-plan.md).

## Features
- **✅ Complete Migration Pipeline**: Parses MapMyRun export CSV, downloads TCX files, validates data, and uploads to Strava
- **🔐 Cookie-Based Downloads**: Uses stable session cookies instead of complex UI automation
- **📊 Progress Tracking**: SQLite database with resume capabilities and real-time status monitoring
- **🎯 Activity Type Prioritization**: Focuses on runs first (configurable with `--skip-non-runs` flag)
- **🔄 Smart Duplicate Handling**: Proactive Strava queries + server-side duplicate rejection handling
- **⚡ Rate Limit Management**: Intelligent backoff-and-retry with dynamic cooldowns based on `Retry-After` headers
- **📈 Comprehensive Reporting**: Activity-type breakdowns, success metrics, and audit trail
- **🛠️ Database Inspection Tools**: Real-time monitoring, CSV exports, and interactive SQL queries
- **🔧 Robust Error Handling**: Graceful handling of various upload errors with detailed diagnostics

## Prerequisites
- Python 3.8+
- A modern web browser (like Chrome or Firefox) for manual cookie extraction.
- MapMyRun account with an exported workout history CSV.
- Strava account with API app credentials.
- See the [migration plan](docs/mapmyrun-to-strava-migration-plan.md) for full setup details.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/hoovdc/MapMyRun_to_Strava_Migration-TCX_Data_Format.git
   cd MapMyRun_to_Strava_Migration-TCX_Data_Format
   ```
2. Create and activate virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Unix/Mac:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   A pinned `requirements.txt` is already included in the repository, so no manual editing is necessary.

## Usage

### Quick Start
```bash
# Run a simulation to verify configuration
python main.py --dry-run

# Start the migration (focuses on runs by default)
python main.py

# Include all activity types (runs, rides, swims, hikes)
python main.py --include-all-types

# Non-interactive batch processing
python main.py --batch-size 10
```

### Migration Process
1. **Configure `.env`**: Follow the guide at [docs/how-to-download-tcx.md](docs/how-to-download-tcx.md) to get your MapMyRun session cookie and add it, along with your Strava API credentials, to `config/.env`.

2. **Run the migration**: The script will guide you through:
   - Populating a local database from your MapMyRun CSV export
   - Downloading and validating all workout TCX files
   - Authenticating with Strava (one-time browser action)
   - Bulk uploading with configurable batch sizes

3. **Monitor progress**: Use the built-in status summary or database inspection tools to track migration progress in real-time.

### Migration Approach
- **🎯 Activity Prioritization**: Focus on runs first with `--skip-non-runs` flag
- **📊 Progress Tracking**: Real-time status monitoring and comprehensive reporting
- **🔄 Resume Capability**: SQLite database enables stopping and resuming migration

For detailed technical breakdown, see [docs/mapmyrun-to-strava-migration-plan.md](docs/mapmyrun-to-strava-migration-plan.md).

**Warning**: This tool is designed for a one-time personal migration. While robust, always back up your data before running.

## Configuration
- Edit `config/.env` with your Strava API credentials and MapMyRun session cookie.
- Use the `--csv-path` argument to point to a different MapMyRun export file if needed.
- Adjust paths in scripts as needed if you deviate from the default project structure.

## Monitoring and Reporting

### Real-Time Status Monitoring
The tool provides comprehensive progress tracking through multiple methods:

```bash
# Built-in status summary with activity type breakdown
python main.py --dry-run --dry-run-limit 1

# Live dashboard with auto-refresh
python utils/live_audit_dashboard.py

# Quick database status report
python utils/db_status_report.py
```

### Database Inspection During Migration
The tool uses a local SQLite database (`data/progress_tracking_data/migration_progress.db`) with WAL mode for concurrent access:

**Recommended: SQLiteStudio in Read-Only Mode**
1. Install SQLiteStudio (free SQLite database viewer)
2. Add Database → Browse to `data/progress_tracking_data/migration_progress.db`
3. Right-click database → Edit database → Check "Read only"
4. Refresh (F5) periodically to see real-time progress

**Alternative: Command Line Tools**
```bash
# Interactive SQL queries (read-only)
python utils/db_monitor.py interactive

# Generate CSV reports for Excel/LibreOffice
python utils/audit_results_exporter.py
```

### Migration Audit and Validation
```bash
# Comprehensive audit plan (optimized for efficiency)
# See: docs/plan_to_audit_record_status.md

# Export detailed CSV reports by activity type
python utils/audit_results_exporter.py
```

## Contributing
This is a personal project, but contributions are welcome! Fork the repo, create a feature branch, and submit a pull request. Please follow the plan in docs/ and test thoroughly.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 