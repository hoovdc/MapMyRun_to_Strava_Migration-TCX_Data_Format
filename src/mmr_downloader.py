import logging
import time
from pathlib import Path
from xml.etree.ElementTree import ParseError

import requests
from tcxreader.tcxreader import TCXReader
from tqdm import tqdm

from src.tcx_validator import TcxValidator

# Get the logger
logger = logging.getLogger(__name__)

class MmrDownloader:
    def __init__(self, cookie_string, output_dir='data/From_MapMyRun/TCX_downloads'):
        self.base_url = "https://www.mapmyrun.com/workout/export"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True) # Ensure the output directory exists
        self.session = requests.Session()
        
        # Set the entire cookie string in the headers
        self.session.headers.update({
            "Cookie": cookie_string,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        
    def download_tcx(self, workout_id):
        """
        Downloads a single TCX file for a given workout ID.
        
        Args:
            workout_id (str or int): The ID of the workout to download.
            
        Returns:
            Path: The path to the downloaded file, or None if download failed.
        """
        try:
            url = f"{self.base_url}/{workout_id}/tcx"
            logger.info(f"Requesting TCX for workout ID: {workout_id} from {url}")
            
            response = self.session.get(url, timeout=30, allow_redirects=False) # Disable redirects
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

            # Check if we got an XML file, not HTML
            if 'text/html' in response.headers.get('Content-Type', ''):
                logger.error(f"Authentication failed for workout ID {workout_id}. Server returned an HTML page instead of TCX data. Please update your cookie string.")
                # Save the HTML for debugging
                debug_path = self.output_dir / f"{workout_id}_error.html"
                debug_path.write_text(response.text)
                logger.info(f"Saved debug HTML to {debug_path}")
                return None
            
            # The Content-Disposition header might suggest a filename, but we will create our own
            file_path = self.output_dir / f"{workout_id}.tcx"
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"Successfully downloaded and saved TCX file to: {file_path}")
            return file_path
            
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 302:
                logger.error(f"Authentication failed for workout ID {workout_id} (Redirected to login). Please update your cookie string.")
                return None
            if http_err.response.status_code == 401:
                logger.error(f"Authentication failed for workout ID {workout_id}. The cookie string may be invalid or expired.")
            elif http_err.response.status_code == 404:
                logger.error(f"Workout ID {workout_id} not found (404). It may not exist or is private.")
            else:
                logger.error(f"HTTP error occurred for workout ID {workout_id}: {http_err}")
            return None
        except requests.exceptions.RequestException as req_err:
            logger.error(f"A request error occurred for workout ID {workout_id}: {req_err}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while downloading workout ID {workout_id}: {e}")
            return None
        
    def batch_download(self, workout_ids: list, delay_seconds: int = 2):
        """
        Downloads and validates a batch of TCX files with a progress bar and rate limiting.

        Args:
            workout_ids: A list of workout IDs to download.
            delay_seconds: The number of seconds to wait between downloads.
        
        Returns:
            A tuple containing the count of successful and failed downloads.
        """
        if not workout_ids:
            logger.warning("No workout IDs provided for batch download.")
            return 0, 0

        successful_downloads = 0
        failed_downloads = 0
        validator = TcxValidator()

        logger.info(f"Starting batch download of {len(workout_ids)} workouts...")

        with tqdm(total=len(workout_ids), desc="Downloading TCX Files") as pbar:
            for workout_id in workout_ids:
                # Check if the file already exists
                file_path = self.output_dir / f"{workout_id}.tcx"
                if file_path.exists():
                    logger.info(f"Skipping workout {workout_id}, file already exists at {file_path}")
                    successful_downloads += 1
                    pbar.update(1)
                    continue

                downloaded_file_path = self.download_tcx(workout_id)

                if downloaded_file_path and validator.validate(str(downloaded_file_path)):
                    successful_downloads += 1
                else:
                    failed_downloads += 1
                
                pbar.update(1)
                
                # Rate limiting
                if workout_id != workout_ids[-1]: # Don't sleep after the last download
                    time.sleep(delay_seconds)
        
        logger.info(f"Batch download complete. Successful: {successful_downloads}, Failed: {failed_downloads}.")
        return successful_downloads, failed_downloads 