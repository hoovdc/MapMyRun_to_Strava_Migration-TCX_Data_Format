# MapMyRun to Strava Migration Tool

This is a Python-based automation tool for migrating fitness workout data from MapMyRun to Strava using TCX file exports. It handles CSV analysis, TCX downloads (with temporary public visibility for simplification), validation, and bulk uploads to Strava.

**Note**: This project is designed for a one-time personal migration of approximately 600 workouts. It temporarily requires making MapMyRun workouts public during the process (reverted afterward). For detailed planning, see [docs/mapmyrun-to-strava-migration-plan.md](docs/mapmyrun-to-strava-migration-plan.md).

## Features
- Parses MapMyRun export CSV to inventory workouts
- Downloads TCX files (simplified via public visibility)
- Validates and repairs TCX files (preserving GPS, heart rate, etc.)
- Authenticates and uploads to Strava in gradual batches
- Error handling, rate limiting, and progress tracking

## Prerequisites
- Python 3.8+
- Chrome browser (for any potential Selenium use, though optional with public workouts)
- MapMyRun account with exported CSV
- Strava account with API app credentials
- See Phase 0 in the [migration plan](docs/mapmyrun-to-strava-migration-plan.md) for full setup.

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
1. Configure `.env` in `config/` with your credentials (see plan for details).
2. Temporarily make MapMyRun workouts public (as per plan).
3. Run the main script:
   ```bash
   python main.py
   ```
4. Follow prompts for migration phases.
5. After completion, revert workouts to private and verify in Strava.

For step-by-step execution, follow the phases in [docs/mapmyrun-to-strava-migration-plan.md](docs/mapmyrun-to-strava-migration-plan.md).

**Warning**: Respect API rate limits. Backup data before running. This is for personal use; adapt for your needs.

## Configuration
- Edit `config/.env` with your Strava API credentials.
- **For MapMyRun authentication**, this project uses a session cookie to bypass the complex login process. Follow the detailed guide at [docs/how-to-download-tcx.md](docs/how-to-download-tcx.md) to get the required cookie string and add it to your `.env` file.
- Adjust paths in scripts as needed.

## Contributing
This is a personal project, but contributions are welcome! Fork the repo, create a feature branch, and submit a pull request. Please follow the plan in docs/ and test thoroughly.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 