"""
Action scheduler for Eclipse Photography Controller.

Executes photographic actions at precise times, replacing the Magic Lantern
scheduling logic with Python equivalents.
"""

import logging
import time
from datetime import datetime, time as time_obj
from typing import Dict, Any

from .time_calculator import TimeCalculator
from .action_types import create_action, ActionType
from ..config.eclipse_config import ActionConfig, CameraSettings
from ..hardware.multi_camera_manager import MultiCameraManager
from ..hardware.camera_controller import format_gphoto2_aperture, format_gphoto2_shutter


class ActionScheduler:
    """
    Scheduler for executing photographic actions.
    
    Equivalent to the action execution logic in the original Magic Lantern script:
    - do_action() -> execute_action()
    - take_shoot() -> execute_photo_action()  
    - boucle() -> execute_loop_action()
    """
    
    def __init__(self, camera_manager: MultiCameraManager, time_calculator: TimeCalculator, test_mode: bool = False):
        """
        Initialize action scheduler.
        
        Args:
            camera_manager: Multi-camera manager for hardware control
            time_calculator: Time calculation utilities
            test_mode: If True, simulate actions without actual photography
        """
        self.camera_manager = camera_manager
        self.time_calculator = time_calculator
        self.test_mode = test_mode
        self.logger = logging.getLogger('action_scheduler')
        
        # Statistics tracking
        self.actions_executed = 0
        self.photos_taken = 0
        self.execution_errors = 0
    
    def execute_action(self, action_config: ActionConfig) -> bool:
        """
        Execute a single action based on its type.
        
        Args:
            action_config: Action configuration to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        try:
            # Create action object for validation
            action = create_action(action_config)
            
            self.logger.info(f"Executing action: {action.get_description()}")
            
            # Route to appropriate execution method
            if action.action_type == ActionType.PHOTO:
                success = self.execute_photo_action(action_config)
            elif action.action_type == ActionType.LOOP:
                success = self.execute_loop_action(action_config)
            elif action.action_type == ActionType.INTERVAL:
                success = self.execute_interval_action(action_config)
            else:
                self.logger.error(f"Unknown action type: {action_config.action_type}")
                success = False
            
            if success:
                self.actions_executed += 1
                self.logger.info(f"Action completed successfully")
            else:
                self.execution_errors += 1
                self.logger.error(f"Action execution failed")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error executing action: {e}", exc_info=True)
            self.execution_errors += 1
            return False
    
    def execute_photo_action(self, action: ActionConfig) -> bool:
        """
        Execute a single photo action.
        
        Equivalent to Magic Lantern take_shoot() function.
        
        Args:
            action: Photo action configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate trigger time
            trigger_time = self._calculate_action_time(action, 'start')
            
            self.logger.info(f"Photo action scheduled for {trigger_time}")
            
            # Configure cameras with action settings
            if not self._configure_cameras_for_action(action):
                return False
            
            # Apply mirror lockup if specified
            if action.mlu_delay > 0:
                self._apply_mirror_lockup(action.mlu_delay)
            
            # Wait until trigger time
            self.time_calculator.wait_until(trigger_time)
            
            # Execute capture
            self.logger.info(f"Triggering photo capture at {datetime.now().time()}")
            capture_results = self.camera_manager.capture_all(self.test_mode)
            
            # Count successful captures
            successful_captures = sum(1 for result in capture_results.values() if result is not None)
            total_cameras = len(capture_results)
            
            self.photos_taken += successful_captures
            
            if successful_captures > 0:
                self.logger.info(f"Photo capture complete: {successful_captures}/{total_cameras} successful")
                return True
            else:
                self.logger.error("All photo captures failed")
                return False
            
        except Exception as e:
            self.logger.error(f"Error in photo action: {e}", exc_info=True)
            return False
    
    def execute_loop_action(self, action: ActionConfig) -> bool:
        """
        Execute a loop action with regular intervals.
        
        Equivalent to Magic Lantern boucle() function.
        
        Args:
            action: Loop action configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate start and end times
            start_time = self._calculate_action_time(action, 'start')
            end_time = self._calculate_action_time(action, 'end')
            interval_seconds = action.interval_or_count
            
            self.logger.info(f"Loop action: {start_time} -> {end_time}, interval: {interval_seconds}s")
            
            # Validate interval
            if interval_seconds <= 0:
                self.logger.error("Invalid interval for loop action")
                return False
            
            # Configure cameras
            if not self._configure_cameras_for_action(action):
                return False
            
            # Wait for start time
            self.time_calculator.wait_until(start_time)
            
            # Execute loop
            loop_start_time = time.time()
            next_capture_time = loop_start_time
            capture_count = 0
            
            while True:
                current_time = datetime.now().time()
                current_seconds = self.time_calculator.time_to_seconds(current_time)
                end_seconds = self.time_calculator.time_to_seconds(end_time)
                
                # Check if we've passed the end time
                if current_seconds >= end_seconds:
                    break
                
                # Check if it's time for next capture
                if time.time() >= next_capture_time:
                    self.logger.info(f"Loop capture {capture_count + 1} at {current_time}")
                    
                    # Apply mirror lockup if specified
                    if action.mlu_delay > 0:
                        self._apply_mirror_lockup(action.mlu_delay)
                    
                    # Capture with all cameras
                    capture_results = self.camera_manager.capture_all(self.test_mode)
                    
                    # Count successful captures
                    successful_captures = sum(1 for result in capture_results.values() if result is not None)
                    self.photos_taken += successful_captures
                    capture_count += 1
                    
                    if successful_captures == 0:
                        self.logger.warning(f"All captures failed in loop iteration {capture_count}")
                    
                    # Schedule next capture
                    next_capture_time += interval_seconds
                
                # Sleep briefly to avoid busy waiting
                time.sleep(0.1)
            
            self.logger.info(f"Loop action complete: {capture_count} capture iterations")
            return capture_count > 0
            
        except Exception as e:
            self.logger.error(f"Error in loop action: {e}", exc_info=True)
            return False
    
    def execute_interval_action(self, action: ActionConfig) -> bool:
        """
        Execute an interval action with a specific number of photos over time.
        
        Args:
            action: Interval action configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate start and end times
            start_time = self._calculate_action_time(action, 'start')
            end_time = self._calculate_action_time(action, 'end')
            photo_count = int(action.interval_or_count)
            
            # Calculate total duration and interval
            total_duration = self.time_calculator.get_time_difference(start_time, end_time)
            
            if total_duration <= 0:
                self.logger.error("Invalid duration for interval action")
                return False
            
            if photo_count <= 1:
                # Single photo, treat as photo action
                return self.execute_photo_action(action)
            
            # Calculate interval between photos
            interval_seconds = total_duration / (photo_count - 1)  # Distribute evenly including endpoints
            
            self.logger.info(f"Interval action: {photo_count} photos from {start_time} to {end_time}")
            self.logger.info(f"Calculated interval: {interval_seconds:.2f}s")
            
            # Configure cameras
            if not self._configure_cameras_for_action(action):
                return False
            
            # Wait for start time
            self.time_calculator.wait_until(start_time)
            
            # Execute interval captures
            interval_start_time = time.time()
            
            for i in range(photo_count):
                current_time = datetime.now().time()
                
                self.logger.info(f"Interval capture {i + 1}/{photo_count} at {current_time}")
                
                # Apply mirror lockup if specified
                if action.mlu_delay > 0:
                    self._apply_mirror_lockup(action.mlu_delay)
                
                # Capture with all cameras
                capture_results = self.camera_manager.capture_all(self.test_mode)
                
                # Count successful captures
                successful_captures = sum(1 for result in capture_results.values() if result is not None)
                self.photos_taken += successful_captures
                
                if successful_captures == 0:
                    self.logger.warning(f"All captures failed in interval iteration {i + 1}")
                
                # Wait for next capture (except on last iteration)
                if i < photo_count - 1:
                    next_capture_time = interval_start_time + (i + 1) * interval_seconds
                    sleep_time = next_capture_time - time.time()
                    
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            
            self.logger.info(f"Interval action complete: {photo_count} photos taken")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in interval action: {e}", exc_info=True)
            return False
    
    def _calculate_action_time(self, action: ActionConfig, time_type: str) -> time_obj:
        """
        Calculate absolute time for action start or end.
        
        Args:
            action: Action configuration
            time_type: 'start' or 'end'
            
        Returns:
            Calculated absolute time
        """
        if time_type == 'start':
            if action.time_ref == '-':
                # Absolute time
                return action.start_time
            else:
                # Relative time
                return self.time_calculator.convert_relative_time(
                    action.time_ref, action.start_operator, action.start_time
                )
        else:  # time_type == 'end'
            if action.end_time is None:
                raise ValueError("End time not specified for action")
            
            return self.time_calculator.convert_relative_time(
                action.time_ref, action.end_operator, action.end_time
            )
    
    def _configure_cameras_for_action(self, action: ActionConfig) -> bool:
        """
        Configure all cameras with action-specific settings.
        
        Args:
            action: Action configuration containing camera settings
            
        Returns:
            True if configuration was successful, False otherwise
        """
        try:
            # Create camera settings from action config
            settings = CameraSettings(
                iso=action.iso or 1600,  # Default ISO
                aperture=format_gphoto2_aperture(action.aperture) if action.aperture else "f/8",
                shutter=format_gphoto2_shutter(action.shutter_speed) if action.shutter_speed else "1/125"
            )
            
            self.logger.info(f"Configuring cameras: ISO {settings.iso}, {settings.aperture}, {settings.shutter}")
            
            # Apply configuration to all cameras
            config_results = self.camera_manager.configure_all(settings)
            
            # Check if any configurations failed
            failed_configs = [cid for cid, success in config_results.items() if not success]
            
            if failed_configs:
                self.logger.warning(f"Camera configuration failed for cameras: {failed_configs}")
                # Continue anyway - partial failure shouldn't stop the action
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring cameras for action: {e}")
            return False
    
    def _apply_mirror_lockup(self, delay_ms: int):
        """
        Apply mirror lockup delay to all cameras.
        
        Args:
            delay_ms: Mirror lockup delay in milliseconds
        """
        if delay_ms <= 0:
            return
        
        self.logger.info(f"Applying mirror lockup: {delay_ms}ms delay")
        
        try:
            # Apply mirror lockup to all active cameras
            for camera_id in self.camera_manager.active_cameras:
                self.camera_manager.cameras[camera_id].mirror_lockup(True, delay_ms)
            
            # Wait for the specified delay
            time.sleep(delay_ms / 1000.0)
            
        except Exception as e:
            self.logger.error(f"Error applying mirror lockup: {e}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        return {
            'actions_executed': self.actions_executed,
            'photos_taken': self.photos_taken,
            'execution_errors': self.execution_errors,
            'test_mode': self.test_mode
        }
    
    def reset_stats(self):
        """Reset execution statistics."""
        self.actions_executed = 0
        self.photos_taken = 0
        self.execution_errors = 0