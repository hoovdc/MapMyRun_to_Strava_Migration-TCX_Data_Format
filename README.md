# MapMyRun to Strava Migration Tool

This is a Python-based automation tool for migrating fitness workout data from MapMyRun to Strava. It uses a session cookie for reliable TCX file downloads, bypassing the need for complex UI automation, and then handles validation and bulk uploads to Strava.

For detailed project planning and history, see [docs/mapmyrun-to-strava-migration-plan.md](docs/mapmyrun-to-strava-migration-plan.md).

## Features
- Parses MapMyRun export CSV to inventory all workouts.
- Downloads TCX files using a stable, cookie-based `requests` method.
- Validates and repairs TCX files (preserving GPS, heart rate, etc.).
- Authenticates and uploads to Strava in gradual, managed batches.
- Uses a local SQLite database for robust progress tracking and resume capabilities.
- Features an automatic database migration system to handle schema changes gracefully.
- Handles errors, rate limiting, and duplicate detection.

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
   python main.py
   ```
3.  The script will guide you through the process:
    - It first populates a local database from your MapMyRun CSV export.
    - It then downloads and validates all your workout TCX files, prompting you for batch sizes.
    - Finally, it authenticates with Strava (a one-time browser action) and prompts you to begin the bulk upload.

For a detailed technical breakdown, follow the phases in [docs/mapmyrun-to-strava-migration-plan.md](docs/mapmyrun-to-strava-migration-plan.md).

**Warning**: Respect API rate limits. It's always a good idea to back up your data before running a migration. This tool is for personal use; adapt for your own needs.

## Configuration
- Edit `config/.env` with your Strava API credentials and MapMyRun session cookie.
- Adjust paths in scripts as needed if you deviate from the default project structure.

## Contributing
This is a personal project, but contributions are welcome! Fork the repo, create a feature branch, and submit a pull request. Please follow the plan in docs/ and test thoroughly.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 