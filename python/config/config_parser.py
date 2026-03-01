"""
Configuration file parser for Eclipse Photography Controller.

Parses the SOLARECL.TXT format used by the original Magic Lantern script
and converts it to Python data structures.
"""

import re
import logging
from datetime import time
from typing import List, Optional
from pathlib import Path

from .eclipse_config import (
    EclipseTimings, ActionConfig, VerificationConfig, SystemConfig
)


class ConfigParserError(Exception):
    """Custom exception for configuration parsing errors."""
    def __init__(self, message: str, line_number: Optional[int] = None):
        self.line_number = line_number
        if line_number:
            super().__init__(f"Line {line_number}: {message}")
        else:
            super().__init__(message)


class ConfigParser:
    """
    Parser for eclipse configuration files.
    
    Maintains compatibility with the original SOLARECL.TXT format while
    providing robust error handling and validation.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('config_parser')
        self.time_pattern = re.compile(r'^(\d{1,2}):(\d{2}):(\d{2})$')
    
    def parse_eclipse_config(self, filename: str) -> SystemConfig:
        """
        Parse complete eclipse configuration file.
        
        Args:
            filename: Path to configuration file
            
        Returns:
            SystemConfig object with all parsed configuration
            
        Raises:
            ConfigParserError: For parsing or validation errors
            FileNotFoundError: If configuration file doesn't exist
        """
        config_path = Path(filename)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filename}")
        
        # Initialize parsing state
        eclipse_timings = None
        verification = None
        actions = []
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        # Parse fields - handle both comma and colon separators
                        fields = self._split_config_line(line)
                        
                        if not fields:
                            continue
                        
                        # Route to appropriate parser based on first field
                        action_type = fields[0]
                        
                        if action_type == 'Verif':
                            verification = self._parse_verification(fields, line_num)
                        elif action_type == 'Config':
                            eclipse_timings = self._parse_config(fields, line_num)
                        elif action_type in ['Photo', 'Boucle', 'Interval']:
                            actions.append(self._parse_action(fields, line_num))
                        else:
                            self.logger.warning(f"Line {line_num}: Unknown action type '{action_type}'")
                    
                    except ConfigParserError:
                        raise
                    except Exception as e:
                        raise ConfigParserError(f"Unexpected error: {e}", line_num)
        
        except UnicodeDecodeError as e:
            raise ConfigParserError(f"File encoding error: {e}")
        
        # Validate required configuration
        if eclipse_timings is None:
            raise ConfigParserError("Missing required 'Config' line with eclipse timings")
        
        if not actions:
            raise ConfigParserError("No photo actions defined")
        
        # Build system configuration
        return SystemConfig(
            eclipse_timings=eclipse_timings,
            verification=verification,
            actions=actions
        )
    
    def _split_config_line(self, line: str) -> List[str]:
        """
        Split configuration line handling both comma and time separators.
        
        Preserves time format (HH:MM:SS) while splitting on commas.
        """
        # First split by comma
        raw_fields = [f.strip() for f in line.split(',')]
        
        # Filter out empty fields
        fields = [f for f in raw_fields if f]
        
        return fields
    
    def _parse_time_string(self, time_str: str, line_num: int) -> time:
        """
        Parse time string in HH:MM:SS format.
        
        Args:
            time_str: Time string to parse
            line_num: Line number for error reporting
            
        Returns:
            time object
            
        Raises:
            ConfigParserError: If time format is invalid
        """
        match = self.time_pattern.match(time_str.strip())
        if not match:
            raise ConfigParserError(f"Invalid time format '{time_str}', expected HH:MM:SS", line_num)
        
        hours, minutes, seconds = map(int, match.groups())
        
        # Validate ranges
        if not (0 <= hours <= 23):
            raise ConfigParserError(f"Invalid hour {hours}, must be 0-23", line_num)
        if not (0 <= minutes <= 59):
            raise ConfigParserError(f"Invalid minute {minutes}, must be 0-59", line_num)
        if not (0 <= seconds <= 59):
            raise ConfigParserError(f"Invalid second {seconds}, must be 0-59", line_num)
        
        return time(hours, minutes, seconds)
    
    def _parse_config(self, fields: List[str], line_num: int) -> EclipseTimings:
        """
        Parse Config line with eclipse contact timings.
        
        Expected format:
        Config,C1_time,C2_time,Max_time,C3_time,C4_time,test_mode
        
        Example:
        Config,14:41:05,16:02:49,16:03:53,16:04:58,17:31:03,1
        """
        if len(fields) < 7:
            raise ConfigParserError(f"Config line requires 7 fields, got {len(fields)}", line_num)
        
        try:
            c1 = self._parse_time_string(fields[1], line_num)
            c2 = self._parse_time_string(fields[2], line_num)
            max_time = self._parse_time_string(fields[3], line_num)
            c3 = self._parse_time_string(fields[4], line_num)
            c4 = self._parse_time_string(fields[5], line_num)
            test_mode = fields[6].strip() == '1'
            
            # Validate eclipse timing sequence (basic check)
            times = [c1, c2, max_time, c3, c4]
            for i in range(len(times) - 1):
                if self._time_to_seconds(times[i]) >= self._time_to_seconds(times[i + 1]):
                    self.logger.warning(f"Line {line_num}: Eclipse times may not be in chronological order")
            
            return EclipseTimings(c1, c2, max_time, c3, c4, test_mode)
            
        except (ValueError, IndexError) as e:
            raise ConfigParserError(f"Error parsing Config line: {e}", line_num)
    
    def _parse_verification(self, fields: List[str], line_num: int) -> VerificationConfig:
        """
        Parse Verif line with camera verification settings.
        
        Original SOLARECL.TXT format:
        Verif,Mode,AF,Battery,FreeSpace
        
        Values of '-' mean 'do not check'.
        Example: Verif,3,0,20,4000
        """
        if len(fields) < 5:
            self.logger.warning(f"Line {line_num}: Verif line has {len(fields)} fields, expected 5")
            return VerificationConfig()
        
        try:
            expected_mode = fields[1].strip() if fields[1].strip() != '-' else None
            expected_af = fields[2].strip() if fields[2].strip() != '-' else None
            min_battery = fields[3].strip() if fields[3].strip() != '-' else None
            min_free_space = fields[4].strip() if fields[4].strip() != '-' else None
            
            return VerificationConfig(
                check_mode=(expected_mode is not None),
                check_autofocus=(expected_af is not None),
                check_battery=(min_battery is not None),
                check_storage=(min_free_space is not None),
                expected_mode=expected_mode,
                expected_af=(expected_af == '0') if expected_af is not None else False,
                min_battery_level=int(min_battery) if min_battery else None,
                min_free_space_mb=int(min_free_space) if min_free_space else None
            )
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Line {line_num}: Error parsing Verif line: {e}")
            return VerificationConfig()
    
    def _parse_action(self, fields: List[str], line_num: int) -> ActionConfig:
        """
        Parse action line (Photo, Boucle, or Interval).
        
        Supports two formats:
        
        Original SOLARECL.TXT format (11 fields for Boucle/Interval):
            Boucle,time_ref,start_op,start_time,end_op,end_time,interval,aperture,iso,shutter,mlu
            Interval,time_ref,start_op,start_time,end_op,end_time,count,aperture,iso,shutter,mlu
        
        Extended format (13 fields, with placeholder dashes):
            Photo,time_ref,start_op,start_time,_,_,_,_,_,aperture,iso,shutter,mlu
            Boucle,time_ref,start_op,start_time,end_op,end_time,interval,_,_,aperture,iso,shutter,mlu
            Interval,time_ref,start_op,start_time,end_op,end_time,count,_,_,aperture,iso,shutter,mlu
        """
        action_type = fields[0]
        
        # Determine camera settings offset based on action type and field count
        if action_type == 'Photo':
            if len(fields) < 13:
                raise ConfigParserError(
                    f"Photo line requires at least 13 fields, got {len(fields)}", line_num)
            camera_offset = 9
        elif action_type in ['Boucle', 'Interval']:
            if len(fields) >= 13:
                # Extended format with placeholder dashes at positions 7 and 8
                camera_offset = 9
            elif len(fields) >= 11:
                # Original SOLARECL.TXT format (no placeholders)
                camera_offset = 7
            else:
                raise ConfigParserError(
                    f"{action_type} line requires at least 11 fields, got {len(fields)}", line_num)
        else:
            raise ConfigParserError(f"Unknown action type '{action_type}'", line_num)
        
        try:
            time_ref = fields[1]
            start_operator = fields[2]
            start_time = self._parse_time_string(fields[3], line_num)
            
            # Camera settings at detected offset
            aperture = float(fields[camera_offset]) if fields[camera_offset] and fields[camera_offset] != '-' else None
            iso = int(float(fields[camera_offset + 1])) if fields[camera_offset + 1] and fields[camera_offset + 1] != '-' else None
            shutter_speed = float(fields[camera_offset + 2]) if fields[camera_offset + 2] and fields[camera_offset + 2] != '-' else None
            mlu_delay = int(float(fields[camera_offset + 3])) if fields[camera_offset + 3] and fields[camera_offset + 3] != '-' else 0
            
            # Validate time reference
            if time_ref not in ['C1', 'C2', 'Max', 'C3', 'C4', '-']:
                raise ConfigParserError(f"Invalid time reference '{time_ref}'", line_num)
            
            # Validate operator
            if start_operator not in ['+', '-', '']:
                raise ConfigParserError(f"Invalid start operator '{start_operator}'", line_num)
            
            if action_type == 'Photo':
                return ActionConfig(
                    action_type=action_type,
                    time_ref=time_ref,
                    start_operator=start_operator,
                    start_time=start_time,
                    aperture=aperture,
                    iso=iso,
                    shutter_speed=shutter_speed,
                    mlu_delay=mlu_delay
                )
            
            elif action_type in ['Boucle', 'Interval']:
                end_operator = fields[4]
                end_time = self._parse_time_string(fields[5], line_num)
                interval_or_count = float(fields[6]) if fields[6] and fields[6] != '-' else None
                
                if end_operator not in ['+', '-', '']:
                    raise ConfigParserError(f"Invalid end operator '{end_operator}'", line_num)
                
                return ActionConfig(
                    action_type=action_type,
                    time_ref=time_ref,
                    start_operator=start_operator,
                    start_time=start_time,
                    end_operator=end_operator,
                    end_time=end_time,
                    interval_or_count=interval_or_count,
                    aperture=aperture,
                    iso=iso,
                    shutter_speed=shutter_speed,
                    mlu_delay=mlu_delay
                )
            
            else:
                raise ConfigParserError(f"Unknown action type '{action_type}'", line_num)
        
        except (ValueError, IndexError) as e:
            raise ConfigParserError(f"Error parsing {fields[0]} action: {e}", line_num)
    
    def _time_to_seconds(self, t: time) -> int:
        """Convert time to seconds since midnight."""
        return t.hour * 3600 + t.minute * 60 + t.second


# Utility function for external use
def parse_config_file(filename: str) -> SystemConfig:
    """
    Convenience function to parse a configuration file.
    
    Args:
        filename: Path to configuration file
        
    Returns:
        SystemConfig object
    """
    parser = ConfigParser()
    return parser.parse_eclipse_config(filename)