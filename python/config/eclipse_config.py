"""
Configuration data structures for Eclipse Photography Controller.

Defines the core data classes used throughout the application for
storing eclipse timings, action configurations, and camera settings.
"""

from dataclasses import dataclass
from datetime import time
from typing import Optional, List


@dataclass
class EclipseTimings:
    """Eclipse contact timings and configuration."""
    c1: time  # Premier contact (First contact)
    c2: time  # Début totalité (Second contact - start of totality)
    max: time  # Maximum (Greatest eclipse)
    c3: time  # Fin totalité (Third contact - end of totality)
    c4: time  # Dernier contact (Fourth contact)
    test_mode: bool = False


@dataclass
class ActionConfig:
    """Configuration for a single photographic action."""
    action_type: str  # 'Photo', 'Boucle', 'Interval'
    time_ref: str     # 'C1', 'C2', 'Max', 'C3', 'C4', '-' (absolute)
    start_operator: str  # '+', '-'
    start_time: time
    end_operator: Optional[str] = None    # '+', '-' (for Boucle/Interval)
    end_time: Optional[time] = None       # (for Boucle/Interval)
    interval_or_count: Optional[float] = None  # seconds or count
    aperture: Optional[float] = None      # f-number (e.g., 8.0 for f/8)
    iso: Optional[int] = None
    shutter_speed: Optional[float] = None # seconds (e.g., 0.008 for 1/125)
    mlu_delay: int = 0                    # Mirror lockup delay in milliseconds
    camera_ids: Optional[List[int]] = None # Specific camera IDs (future use)

    def __post_init__(self):
        """Validate action configuration after initialization."""
        if self.action_type in ['Boucle', 'Interval']:
            if self.end_time is None or self.interval_or_count is None:
                raise ValueError(f"{self.action_type} requires end_time and interval_or_count")


@dataclass
class VerificationConfig:
    """Camera verification settings."""
    check_battery: bool = True
    check_storage: bool = True
    check_mode: bool = True
    check_autofocus: bool = True
    min_battery_level: Optional[int] = None  # Percentage
    min_free_space_mb: Optional[int] = None


@dataclass
class CameraSettings:
    """Camera configuration settings for GPhoto2."""
    iso: int
    aperture: str      # "f/8", "f/11", etc. (GPhoto2 format)
    shutter: str       # "1/125", "2", etc. (GPhoto2 format)


@dataclass
class CameraStatus:
    """Current camera status information."""
    battery_level: Optional[int] = None  # Percentage
    free_space_mb: Optional[int] = None  # Megabytes
    mode: str = "Unknown"
    af_enabled: bool = False
    connected: bool = False
    last_error: Optional[str] = None


@dataclass
class SystemConfig:
    """Overall system configuration."""
    eclipse_timings: EclipseTimings
    verification: Optional[VerificationConfig]
    actions: List[ActionConfig]
    test_mode: bool = False
    log_level: str = "INFO"
    camera_ids: Optional[List[int]] = None  # Restrict to specific cameras