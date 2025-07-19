import logging
from xml.etree.ElementTree import ParseError
from tcxreader.tcxreader import TCXReader, TCXTrackPoint

logger = logging.getLogger(__name__)

class TcxValidator:
    """
    Validates TCX files using the tcxreader library.
    """
    def validate(self, file_path: str) -> bool:
        """
        Validates a TCX file by attempting to parse it and checking for essential and detailed data.

        Args:
            file_path: The path to the TCX file.

        Returns:
            True if the file is a valid and non-empty TCX file, False otherwise.
        """
        try:
            tcx = TCXReader().read(str(file_path))

            # A workout is valid if it has a duration OR trackpoints. This handles indoor activities.
            has_duration = tcx.duration is not None and tcx.duration > 0
            has_trackpoints = tcx.trackpoints and len(tcx.trackpoints) > 0

            if not has_duration and not has_trackpoints:
                logger.error(f"Validation FAILED for {file_path}: File has no duration or trackpoints.")
                return False

            # High-level success message for console
            logger.info(f"Validation SUCCESS for {file_path}")

            # Detailed data logging for the log file
            logger.debug(f"--- Detailed Validation Report for {file_path} ---")
            
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
            
            logger.debug(f"--- End of Report for {file_path} ---")

            return True

        except (ParseError) as e:
            logger.error(f"Validation FAILED for {file_path}: Malformed XML/TCX file. Details: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during TCX validation of {file_path}: {e}")
            return False 