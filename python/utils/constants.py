"""
Constants for Eclipse Photography Controller.

Defines constants and mappings used throughout the application.
"""

# Application metadata
APP_NAME = "Eclipse Photography Controller"
APP_VERSION = "3.0.0"
APP_DESCRIPTION = "Python/GPhoto2 migration of Magic Lantern eclipse_OZ.lua script"

# Default camera settings
DEFAULT_ISO = 1600
DEFAULT_APERTURE = "f/8"
DEFAULT_SHUTTER = "1/125"
DEFAULT_MLU_DELAY = 0  # milliseconds

# Time reference constants
TIME_REFERENCES = ['C1', 'C2', 'Max', 'C3', 'C4', '-']
TIME_OPERATORS = ['+', '-']

# Action types
ACTION_TYPES = ['Photo', 'Boucle', 'Interval']

# Camera validation thresholds
MIN_BATTERY_LEVEL = 20  # percent
MIN_FREE_SPACE_MB = 100  # megabytes
MAX_CAPTURE_TIMEOUT = 30  # seconds

# Timing constraints
MAX_WAIT_TIME = 24 * 3600  # 24 hours in seconds
MIN_INTERVAL = 0.1  # minimum interval between captures in seconds
DEFAULT_CHECK_INTERVAL = 0.25  # default time check interval in seconds

# Eclipse timing constraints (for validation)
MAX_TOTALITY_DURATION = 7 * 60 + 32  # Maximum possible totality ~7m32s in seconds
MIN_ECLIPSE_DURATION = 30 * 60  # Minimum reasonable eclipse duration ~30 minutes

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# File extensions
CONFIG_FILE_EXTENSIONS = ['.txt', '.cfg', '.conf']
IMAGE_FILE_EXTENSIONS = ['.jpg', '.jpeg', '.cr2', '.cr3', '.raw']

# GPhoto2 mapping tables
GPHOTO2_ISO_VALUES = [
    "100", "125", "160", "200", "250", "320", "400", "500", "640", 
    "800", "1000", "1250", "1600", "2000", "2500", "3200", "4000", 
    "5000", "6400", "8000", "10000", "12800", "16000", "20000", "25600"
]

GPHOTO2_APERTURE_VALUES = [
    "f/1.0", "f/1.1", "f/1.2", "f/1.4", "f/1.6", "f/1.8", "f/2.0", 
    "f/2.2", "f/2.5", "f/2.8", "f/3.2", "f/3.5", "f/4.0", "f/4.5", 
    "f/5.0", "f/5.6", "f/6.3", "f/7.1", "f/8", "f/9", "f/10", "f/11", 
    "f/13", "f/14", "f/16", "f/18", "f/20", "f/22", "f/25", "f/29", "f/32"
]

GPHOTO2_SHUTTER_VALUES = [
    "30", "25", "20", "15", "13", "10", "8", "6", "5", "4", "3.2", 
    "2.5", "2", "1.6", "1.3", "1", "0.8", "0.6", "0.5", "0.4", "0.3", 
    "1/4", "1/5", "1/6", "1/8", "1/10", "1/13", "1/15", "1/20", "1/25", 
    "1/30", "1/40", "1/50", "1/60", "1/80", "1/100", "1/125", "1/160", 
    "1/200", "1/250", "1/320", "1/400", "1/500", "1/640", "1/800", 
    "1/1000", "1/1250", "1/1600", "1/2000", "1/2500", "1/3200", "1/4000"
]

# Error messages
ERROR_MESSAGES = {
    'no_cameras': "No cameras detected. Please check USB connections.",
    'config_parse_error': "Error parsing configuration file",
    'invalid_time_format': "Invalid time format. Expected HH:MM:SS",
    'invalid_eclipse_sequence': "Eclipse times not in chronological order",
    'camera_config_failed': "Failed to configure camera settings",
    'capture_failed': "Photo capture failed",
    'connection_failed': "Failed to connect to camera"
}

# Success messages
SUCCESS_MESSAGES = {
    'cameras_connected': "All cameras connected successfully",
    'config_loaded': "Configuration loaded successfully",
    'sequence_complete': "Eclipse sequence completed successfully",
    'validation_passed': "System validation passed"
}

# Configuration file field counts
CONFIG_FIELD_COUNTS = {
    'Config': 7,    # Config,C1,C2,Max,C3,C4,test_mode
    'Photo': 13,    # Photo,time_ref,op,time,_,_,_,_,_,aperture,iso,shutter,mlu
    'Boucle': 13,   # Boucle,time_ref,op,start,op,end,interval,_,_,aperture,iso,shutter,mlu
    'Interval': 13, # Interval,time_ref,op,start,op,end,count,_,_,aperture,iso,shutter,mlu
    'Verif': 5      # Verif,battery,storage,mode,af (simplified)
}