# MapMyRun to Strava Migration Tool

This is a Python-based automation tool for migrating fitness workout data from MapMyRun to Strava. It uses a session cookie for reliable TCX file downloads, bypassing the need for complex UI automation, and then handles validation and bulk uploads to Strava.

For detailed project planning and history, see [docs/mapmyrun-to-strava-migration-plan.md](docs/mapmyrun-to-strava-migration-plan.md).

## Features
- Parses MapMyRun export CSV to inventory all workouts.
- Downloads TCX files using a stable, cookie-based `requests` method.
- Validates TCX files, with robust handling for workouts lacking GPS data.
- Authenticates with Strava using a self-refreshing OAuth2 token.
- Uses a local SQLite database for robust progress tracking and resume capabilities.
- **Advanced Error Handling**: Includes intelligent backoff-and-retry for API rate limits and resilient handling of various upload errors.
- **Proactive Duplicate Detection**: Queries Strava for existing activities to prevent unnecessary uploads, in addition to handling Strava's server-side duplicate rejection.
- Includes a post-migration audit tool to identify potential duplicates on Strava.

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
1.  **Configure `.env`**: Follow the guide at [docs/how-to-download-tcx.md](docs/how-to-download-tcx.md) to get your MapMyRun session cookie and add it, along with your Strava API credentials, to `config/.env`.
2.  **Run the main script**:
   ```bash
   # Run a full simulation first to ensure everything is configured correctly
   python main.py --dry-run

   # Once verified, run the live migration
   python main.py
   ```
3.  The script will guide you through the process:
    - It first populates a local database from your MapMyRun CSV export.
    - It then downloads and validates all your workout TCX files, prompting you for batch sizes.
    - Finally, it authenticates with Strava (a one-time browser action) and prompts you to begin the bulk upload.

For a detailed technical breakdown, follow the phases in [docs/mapmyrun-to-strava-migration-plan.md](docs/mapmyrun-to-strava-migration-plan.md).

**Warning**: This tool is designed for a one-time personal migration. While robust, always back up your data before running.

## Configuration
- Edit `config/.env` with your Strava API credentials and MapMyRun session cookie.
- Use the `--csv-path` argument to point to a different MapMyRun export file if needed.
- Adjust paths in scripts as needed if you deviate from the default project structure.

## Contributing
This is a personal project, but contributions are welcome! Fork the repo, create a feature branch, and submit a pull request. Please follow the plan in docs/ and test thoroughly.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 