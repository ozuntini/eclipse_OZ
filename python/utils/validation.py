"""
System validation utilities for Eclipse Photography Controller.

Provides system and camera validation functions to ensure the system
is ready for eclipse photography.
"""

import logging
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from config.eclipse_config import SystemConfig, VerificationConfig, CameraStatus
from hardware.multi_camera_manager import MultiCameraManager
from .constants import MIN_BATTERY_LEVEL, MIN_FREE_SPACE_MB, ERROR_MESSAGES


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class SystemValidator:
    """
    System and hardware validation utilities.
    
    Equivalent to the verification functions in the original Magic Lantern script.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('system_validator')
    
    def validate_system(self) -> bool:
        """
        Validate overall system readiness.
        
        Returns:
            True if system is ready, False otherwise
        """
        self.logger.info("Starting system validation...")
        
        validation_results = {
            'python_version': self._validate_python_version(),
            'gphoto2_availability': self._validate_gphoto2(),
            'usb_permissions': self._validate_usb_permissions(),
            'storage_space': self._validate_storage_space(),
            'time_sync': self._validate_time_sync()
        }
        
        # Log validation results
        for check, result in validation_results.items():
            status = "✓" if result else "✗"
            self.logger.info(f"{status} {check}")
        
        overall_result = all(validation_results.values())
        
        if overall_result:
            self.logger.info("System validation passed")
        else:
            failed_checks = [check for check, result in validation_results.items() if not result]
            self.logger.error(f"System validation failed: {', '.join(failed_checks)}")
        
        return overall_result
    
    def validate_cameras(self, camera_manager: MultiCameraManager, 
                        verification_config: Optional[VerificationConfig] = None) -> bool:
        """
        Validate camera readiness for photography.
        
        Args:
            camera_manager: Multi-camera manager instance
            verification_config: Optional verification configuration
            
        Returns:
            True if all cameras are ready, False otherwise
        """
        if verification_config is None:
            verification_config = VerificationConfig()
        
        self.logger.info("Starting camera validation...")
        
        # Get status of all cameras
        camera_status = camera_manager.get_all_status()
        
        if not camera_status:
            self.logger.error("No cameras available for validation")
            return False
        
        validation_results = {}
        
        for camera_id, status in camera_status.items():
            camera_name = camera_manager.cameras[camera_id].name
            self.logger.info(f"Validating {camera_name}...")
            
            camera_validation = {
                'connected': self._validate_camera_connection(status),
                'battery': self._validate_battery_level(status, verification_config),
                'storage': self._validate_storage_space_camera(status, verification_config),
                'mode': self._validate_camera_mode(status, verification_config),
                'autofocus': self._validate_autofocus(status, verification_config)
            }
            
            validation_results[camera_id] = camera_validation
            
            # Log camera-specific results
            for check, result in camera_validation.items():
                status_icon = "✓" if result else "✗"
                self.logger.info(f"  {status_icon} {camera_name} {check}")
        
        # Check overall camera readiness
        all_cameras_ready = all(
            all(checks.values()) 
            for checks in validation_results.values()
        )
        
        if all_cameras_ready:
            self.logger.info("All cameras validated successfully")
        else:
            failed_cameras = []
            for camera_id, checks in validation_results.items():
                if not all(checks.values()):
                    camera_name = camera_manager.cameras[camera_id].name
                    failed_checks = [check for check, result in checks.items() if not result]
                    failed_cameras.append(f"{camera_name}: {', '.join(failed_checks)}")
            
            self.logger.error(f"Camera validation failed: {'; '.join(failed_cameras)}")
        
        return all_cameras_ready
    
    def validate_configuration(self, config: SystemConfig) -> bool:
        """
        Validate eclipse configuration.
        
        Args:
            config: System configuration to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        self.logger.info("Validating eclipse configuration...")
        
        validation_results = {
            'eclipse_timings': self._validate_eclipse_timings(config),
            'action_sequence': self._validate_action_sequence(config),
            'camera_settings': self._validate_camera_settings(config)
        }
        
        for check, result in validation_results.items():
            status = "✓" if result else "✗"
            self.logger.info(f"{status} {check}")
        
        overall_result = all(validation_results.values())
        
        if overall_result:
            self.logger.info("Configuration validation passed")
        else:
            self.logger.error("Configuration validation failed")
        
        return overall_result
    
    def _validate_python_version(self) -> bool:
        """Validate Python version compatibility."""
        try:
            version = platform.python_version_tuple()
            major, minor = int(version[0]), int(version[1])
            
            if major < 3 or (major == 3 and minor < 7):
                self.logger.error(f"Python {major}.{minor} not supported. Requires Python 3.7+")
                return False
            
            self.logger.debug(f"Python {major}.{minor} is compatible")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking Python version: {e}")
            return False
    
    def _validate_gphoto2(self) -> bool:
        """Validate GPhoto2 installation and availability."""
        try:
            # Check if gphoto2 command is available
            gphoto2_path = shutil.which('gphoto2')
            if not gphoto2_path:
                self.logger.error("gphoto2 command not found in PATH")
                return False
            
            # Try to import gphoto2 Python module
            try:
                import gphoto2
                self.logger.debug("gphoto2 Python module available")
                return True
            except ImportError:
                self.logger.error("gphoto2 Python module not available")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating GPhoto2: {e}")
            return False
    
    def _validate_usb_permissions(self) -> bool:
        """Validate USB permissions for camera access."""
        try:
            # Check if running on Linux/Pi
            if platform.system() == 'Linux':
                # Check for camera-related udev rules
                udev_rules_path = Path('/etc/udev/rules.d')
                camera_rules = list(udev_rules_path.glob('*canon*.rules')) + \
                              list(udev_rules_path.glob('*camera*.rules'))
                
                if not camera_rules:
                    self.logger.warning("No camera-specific udev rules found. May need manual setup.")
                    return True  # Don't fail, just warn
                
                self.logger.debug(f"Found camera udev rules: {camera_rules}")
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not validate USB permissions: {e}")
            return True  # Don't fail on permission check errors
    
    def _validate_storage_space(self) -> bool:
        """Validate available storage space on system."""
        try:
            # Check current directory space (cross-platform)
            usage = shutil.disk_usage('.')
            free_space_mb = usage.free / (1024 * 1024)
            
            if free_space_mb < 1000:  # Require at least 1GB
                self.logger.error(f"Insufficient storage space: {free_space_mb:.0f}MB available")
                return False
            
            self.logger.debug(f"Storage space available: {free_space_mb:.0f}MB")
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not validate storage space: {e}")
            return True  # Don't fail if we can't check
    
    def _validate_time_sync(self) -> bool:
        """Validate system time synchronization."""
        try:
            # Basic time validation - could be extended with NTP checks
            import datetime
            now = datetime.datetime.now()
            
            # Check if time seems reasonable (after 2020)
            if now.year < 2020:
                self.logger.error(f"System time seems incorrect: {now}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not validate time sync: {e}")
            return True
    
    def _validate_camera_connection(self, status: CameraStatus) -> bool:
        """Validate camera connection status."""
        return status.connected
    
    def _validate_battery_level(self, status: CameraStatus, config: VerificationConfig) -> bool:
        """Validate camera battery level."""
        if not config.check_battery:
            return True
        
        if status.battery_level is None:
            self.logger.warning("Battery level not available")
            return True  # Don't fail if we can't check
        
        min_level = config.min_battery_level or MIN_BATTERY_LEVEL
        
        if status.battery_level < min_level:
            self.logger.error(f"Low battery: {status.battery_level}% < {min_level}%")
            return False
        
        return True
    
    def _validate_storage_space_camera(self, status: CameraStatus, config: VerificationConfig) -> bool:
        """Validate camera storage space."""
        if not config.check_storage:
            return True
        
        if status.free_space_mb is None:
            self.logger.warning("Camera storage space not available")
            return True  # Don't fail if we can't check
        
        min_space = config.min_free_space_mb or MIN_FREE_SPACE_MB
        
        if status.free_space_mb < min_space:
            self.logger.error(f"Low camera storage: {status.free_space_mb}MB < {min_space}MB")
            return False
        
        return True
    
    def _validate_camera_mode(self, status: CameraStatus, config: VerificationConfig) -> bool:
        """Validate camera mode settings."""
        if not config.check_mode:
            return True
        
        # Basic mode validation - could be extended based on requirements
        if status.mode == "Unknown":
            self.logger.warning("Camera mode unknown")
        
        return True
    
    def _validate_autofocus(self, status: CameraStatus, config: VerificationConfig) -> bool:
        """Validate autofocus configuration."""
        if not config.check_autofocus:
            return True
        
        # For eclipse photography, AF should typically be disabled
        if status.af_enabled:
            self.logger.warning("Autofocus is enabled - consider disabling for eclipse photography")
        
        return True
    
    def _validate_eclipse_timings(self, config: SystemConfig) -> bool:
        """Validate eclipse timing sequence."""
        try:
            # Use time calculator for validation
            from scheduling.time_calculator import TimeCalculator
            calculator = TimeCalculator(config.eclipse_timings)
            return calculator.validate_eclipse_sequence()
            
        except Exception as e:
            self.logger.error(f"Error validating eclipse timings: {e}")
            return False
    
    def _validate_action_sequence(self, config: SystemConfig) -> bool:
        """Validate action sequence for logical consistency."""
        try:
            if not config.actions:
                self.logger.error("No actions defined")
                return False
            
            # Validate each action
            from scheduling.action_types import create_action
            
            for i, action_config in enumerate(config.actions):
                try:
                    action = create_action(action_config)
                    self.logger.debug(f"Action {i + 1}: {action.get_description()}")
                except Exception as e:
                    self.logger.error(f"Invalid action {i + 1}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating action sequence: {e}")
            return False
    
    def _validate_camera_settings(self, config: SystemConfig) -> bool:
        """Validate camera settings in actions."""
        try:
            for i, action in enumerate(config.actions):
                # Check for reasonable camera settings
                if action.iso and (action.iso < 100 or action.iso > 25600):
                    self.logger.warning(f"Action {i + 1}: Unusual ISO value {action.iso}")
                
                if action.aperture and (action.aperture < 1.0 or action.aperture > 32):
                    self.logger.warning(f"Action {i + 1}: Unusual aperture f/{action.aperture}")
                
                if action.shutter_speed and (action.shutter_speed < 0.0001 or action.shutter_speed > 30):
                    self.logger.warning(f"Action {i + 1}: Unusual shutter speed {action.shutter_speed}s")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating camera settings: {e}")
            return False