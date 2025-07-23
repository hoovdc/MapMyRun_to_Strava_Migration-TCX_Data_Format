import logging
import re
from xml.etree.ElementTree import ParseError
from tcxreader.tcxreader import TCXReader, TCXTrackPoint
import os

logger = logging.getLogger(__name__)

class TcxValidator:
    """
    Validates TCX files using the tcxreader library.
    """
    def validate(self, file_path: str) -> bool:
        """
        Validates a TCX file by attempting to parse it and checking for essential and detailed data.
        Includes a fallback to manually check for duration if the tcxreader library fails.

        Args:
            file_path: The path to the TCX file.

        Returns:
            True if the file is a valid and non-empty TCX file, False otherwise.
        """
        file_name = os.path.basename(file_path)
        try:
            tcx = TCXReader().read(str(file_path))

            # A workout is valid if it has a duration. It doesn't need GPS.
            if tcx.duration is None or tcx.duration <= 0:
                # Fallback: tcxreader can fail on some files. Manually check for TotalTimeSeconds.
                logger.warning(f"tcxreader found no duration for {file_name}. Attempting manual fallback.")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    match = re.search(r'<TotalTimeSeconds>(\d+\.?\d*)</TotalTimeSeconds>', content)
                    if match:
                        duration = float(match.group(1))
                        if duration > 0:
                            logger.info(f"Fallback SUCCESS: Found duration of {duration}s in {file_name} via manual check.")
                            return True
                except Exception as e:
                    logger.error(f"Fallback FAILED for {file_name} during manual read: {e}")
                    return False

                logger.error(f"Validation FAILED for {file_name}: File has no duration or trackpoints, even after fallback.")
                return False

            # High-level success message for console
            logger.info(f"Validation SUCCESS for {file_name}")

            # Detailed data logging for the log file
            logger.debug(f"--- Detailed Validation Report for {file_name} ---")
            
            if tcx.activity_type:
                logger.debug(f"  Activity Type: {tcx.activity_type}")
            else:
                logger.warning("  Activity Type: Not found.")

            if tcx.end_time:
                logger.debug(f"  End Time: {tcx.end_time}")
            else:
                logger.warning("  End Time: Not found.")

            logger.debug(f"  Total Distance: {round(tcx.distance or 0, 2)} meters")
            logger.debug(f"  Total Duration: {round(tcx.duration or 0, 2)} seconds")
            logger.debug(f"  Average Heart Rate: {tcx.hr_avg}")

            if not tcx.trackpoints:
                logger.warning(f"  Workout has no trackpoints (e.g., manual entry). Duration: {tcx.duration}s")

            total_points = len(tcx.trackpoints)
            if total_points > 0:
                points_with_gps = sum(1 for tp in tcx.trackpoints if tp.latitude is not None and tp.longitude is not None)
                points_with_hr = sum(1 for tp in tcx.trackpoints if tp.hr_value is not None)

                logger.debug(f"  Trackpoints Found: {total_points}")
                logger.debug(f"  Trackpoints with GPS: {points_with_gps} ({round(points_with_gps/total_points * 100, 1)}%)")
                logger.debug(f"  Trackpoints with Heart Rate: {points_with_hr} ({round(points_with_hr/total_points * 100, 1)}%)")
                
                if points_with_gps == 0:
                    logger.warning(f"  This appears to be an indoor activity (no GPS data).")
            
            logger.debug(f"--- End of Report for {file_name} ---")

            return True

        except (ParseError) as e:
            logger.error(f"Validation FAILED for {file_name}: Malformed XML/TCX file. Details: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during TCX validation of {file_name}: {e}")
            return False 