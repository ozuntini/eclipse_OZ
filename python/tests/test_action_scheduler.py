"""
Unit tests for action scheduler.

Tests the execution of photographic actions with proper timing.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import time

from config.eclipse_config import EclipseTimings, ActionConfig
from scheduling.time_calculator import TimeCalculator
from scheduling.action_scheduler import ActionScheduler
from hardware.multi_camera_manager import MultiCameraManager



class TestActionScheduler(unittest.TestCase):
    """Test cases for ActionScheduler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock eclipse timings
        self.timings = EclipseTimings(
            c1=time(14, 41, 5),
            c2=time(16, 2, 49),
            max=time(16, 3, 53),
            c3=time(16, 4, 58),
            c4=time(17, 31, 3),
            test_mode=False
        )
        
        # Create time calculator
        self.time_calculator = TimeCalculator(self.timings)
        
        # Create mock camera manager
        self.camera_manager = Mock(spec=MultiCameraManager)
        self.camera_manager.active_cameras = [0, 1]
        self.camera_manager.cameras = {
            0: Mock(),
            1: Mock()
        }
        self.camera_manager.configure_all.return_value = {0: True, 1: True}
        self.camera_manager.capture_all.return_value = {
            0: "camera0_image.jpg",
            1: "camera1_image.jpg"
        }
        
        # Create scheduler
        self.scheduler = ActionScheduler(
            self.camera_manager,
            self.time_calculator,
            test_mode=True
        )
    
    def test_initialization(self):
        """Test scheduler initialization."""
        self.assertEqual(self.scheduler.camera_manager, self.camera_manager)
        self.assertEqual(self.scheduler.time_calculator, self.time_calculator)
        self.assertTrue(self.scheduler.test_mode)
        self.assertEqual(self.scheduler.actions_executed, 0)
        self.assertEqual(self.scheduler.photos_taken, 0)
        self.assertEqual(self.scheduler.execution_errors, 0)
    
    @patch('scheduling.action_scheduler.time')
    def test_execute_photo_action_absolute_time(self, mock_time):
        """Test execution of photo action with absolute time."""
        # Create photo action with absolute time
        action = ActionConfig(
            action_type="Photo",
            time_ref="-",  # Absolute time
            start_operator="",
            start_time=time(16, 0, 0),
            aperture=8.0,
            iso=1600,
            shutter_speed=0.008,  # 1/125
            mlu_delay=500
        )
        
        # Mock time to simulate reaching target time
        mock_time.time.return_value = 1000
        
        # Mock wait_until to not actually wait
        with patch.object(self.time_calculator, 'wait_until'):
            result = self.scheduler.execute_photo_action(action)
        
        self.assertTrue(result)
        self.camera_manager.configure_all.assert_called_once()
        self.camera_manager.capture_all.assert_called_once_with(True)
        self.assertEqual(self.scheduler.photos_taken, 2)  # 2 cameras
    
    @patch('scheduling.action_scheduler.time')
    def test_execute_photo_action_relative_time(self, mock_time):
        """Test execution of photo action with relative time."""
        # Create photo action with relative time (Max - 10 seconds)
        action = ActionConfig(
            action_type="Photo",
            time_ref="Max",
            start_operator="-",
            start_time=time(0, 0, 10),
            aperture=5.6,
            iso=800,
            shutter_speed=0.004,  # 1/250
            mlu_delay=0
        )
        
        # Mock wait_until to not actually wait
        with patch.object(self.time_calculator, 'wait_until'):
            result = self.scheduler.execute_photo_action(action)
        
        self.assertTrue(result)
        
        # Check that camera configuration was called with correct settings
        call_args = self.camera_manager.configure_all.call_args[0][0]
        self.assertEqual(call_args.iso, 800)
        self.assertEqual(call_args.aperture, "f/5.6")
        self.assertEqual(call_args.shutter, "1/250")
    
    def test_execute_photo_action_camera_failure(self):
        """Test photo action when all cameras fail."""
        action = ActionConfig(
            action_type="Photo",
            time_ref="-",
            start_operator="",
            start_time=time(16, 0, 0),
            aperture=8.0,
            iso=1600,
            shutter_speed=0.008
        )
        
        # Mock all cameras failing
        self.camera_manager.capture_all.return_value = {0: None, 1: None}
        
        with patch.object(self.time_calculator, 'wait_until'):
            result = self.scheduler.execute_photo_action(action)
        
        self.assertFalse(result)
        self.assertEqual(self.scheduler.photos_taken, 0)
    
    @patch('scheduling.action_scheduler.time')
    def test_execute_loop_action(self, mock_time):
        """Test execution of loop action."""
        # Create loop action (C2 + 0 to C2 + 1 minute, every 10 seconds)
        action = ActionConfig(
            action_type="Boucle",
            time_ref="C2",
            start_operator="+",
            start_time=time(0, 0, 0),
            end_operator="+",
            end_time=time(0, 1, 0),
            interval_or_count=10.0,  # 10 seconds
            aperture=4.0,
            iso=1600,
            shutter_speed=0.002  # 1/500
        )
        
        # Mock time progression
        mock_time.time.side_effect = [
            1000,  # Loop start
            1010,  # First capture + interval
            1020,  # Second capture + interval
            1070   # End of loop (beyond end time)
        ]
        
        # Mock current time to simulate progression
        time_sequence = [
            time(16, 2, 49),  # Start time
            time(16, 2, 59),  # During loop
            time(16, 3, 9),   # During loop
            time(16, 3, 49)   # End time reached
        ]
        
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.side_effect = time_sequence
            
            with patch.object(self.time_calculator, 'wait_until'):
                with patch('time.sleep'):  # Don't actually sleep
                    result = self.scheduler.execute_loop_action(action)
        
        self.assertTrue(result)
        # Should have made multiple capture calls
        self.assertGreater(self.camera_manager.capture_all.call_count, 1)
    
    def test_execute_interval_action(self):
        """Test execution of interval action."""
        # Create interval action (5 photos from C2 to C2+1min)
        action = ActionConfig(
            action_type="Interval",
            time_ref="C2",
            start_operator="+",
            start_time=time(0, 0, 0),
            end_operator="+",
            end_time=time(0, 1, 0),
            interval_or_count=5.0,  # 5 photos
            aperture=11.0,
            iso=400,
            shutter_speed=0.001  # 1/1000
        )
        
        with patch.object(self.time_calculator, 'wait_until'):
            with patch('time.sleep'):  # Don't actually sleep
                with patch('time.time', side_effect=[1000, 1015, 1030, 1045, 1060, 1075]):
                    result = self.scheduler.execute_interval_action(action)
        
        self.assertTrue(result)
        # Should have made 5 capture calls
        self.assertEqual(self.camera_manager.capture_all.call_count, 5)
    
    def test_execute_interval_action_single_photo(self):
        """Test interval action with single photo."""
        action = ActionConfig(
            action_type="Interval",
            time_ref="Max",
            start_operator="-",
            start_time=time(0, 0, 5),
            end_operator="+",
            end_time=time(0, 0, 5),
            interval_or_count=1.0,  # 1 photo
            aperture=8.0,
            iso=1600,
            shutter_speed=0.008
        )
        
        with patch.object(self.scheduler, 'execute_photo_action') as mock_photo:
            mock_photo.return_value = True
            result = self.scheduler.execute_interval_action(action)
        
        self.assertTrue(result)
        mock_photo.assert_called_once_with(action)
    
    def test_calculate_action_time_absolute(self):
        """Test action time calculation for absolute time."""
        action = ActionConfig(
            action_type="Photo",
            time_ref="-",
            start_operator="",
            start_time=time(15, 30, 0),
            aperture=8.0,
            iso=1600,
            shutter_speed=0.008
        )
        
        result = self.scheduler._calculate_action_time(action, 'start')
        self.assertEqual(result, time(15, 30, 0))
    
    def test_calculate_action_time_relative(self):
        """Test action time calculation for relative time."""
        action = ActionConfig(
            action_type="Photo",
            time_ref="C2",
            start_operator="+",
            start_time=time(0, 1, 30),
            aperture=8.0,
            iso=1600,
            shutter_speed=0.008
        )
        
        result = self.scheduler._calculate_action_time(action, 'start')
        # C2 + 1:30 = 16:02:49 + 1:30 = 16:04:19
        expected = time(16, 4, 19)
        self.assertEqual(result, expected)
    
    def test_configure_cameras_for_action(self):
        """Test camera configuration for action."""
        action = ActionConfig(
            action_type="Photo",
            time_ref="-",
            start_operator="",
            start_time=time(16, 0, 0),
            aperture=5.6,
            iso=800,
            shutter_speed=0.004  # 1/250
        )
        
        result = self.scheduler._configure_cameras_for_action(action)
        self.assertTrue(result)
        
        # Check configuration call
        call_args = self.camera_manager.configure_all.call_args[0][0]
        self.assertEqual(call_args.iso, 800)
        self.assertEqual(call_args.aperture, "f/5.6")
        self.assertEqual(call_args.shutter, "1/250")
    
    def test_configure_cameras_with_defaults(self):
        """Test camera configuration with default values."""
        action = ActionConfig(
            action_type="Photo",
            time_ref="-",
            start_operator="",
            start_time=time(16, 0, 0)
            # No camera settings specified
        )
        
        result = self.scheduler._configure_cameras_for_action(action)
        self.assertTrue(result)
        
        # Check default values were used
        call_args = self.camera_manager.configure_all.call_args[0][0]
        self.assertEqual(call_args.iso, 1600)  # Default ISO
        self.assertEqual(call_args.aperture, "f/8")  # Default aperture
        self.assertEqual(call_args.shutter, "1/125")  # Default shutter
    
    def test_apply_mirror_lockup(self):
        """Test mirror lockup application."""
        with patch('time.sleep') as mock_sleep:
            self.scheduler._apply_mirror_lockup(500)  # 500ms delay
        
        # Should have called mirror_lockup on all cameras
        for camera_id in self.camera_manager.active_cameras:
            camera = self.camera_manager.cameras[camera_id]
            camera.mirror_lockup.assert_called_with(True, 500)
        
        # Should have slept for 0.5 seconds
        mock_sleep.assert_called_with(0.5)
    
    def test_apply_mirror_lockup_zero_delay(self):
        """Test mirror lockup with zero delay."""
        self.scheduler._apply_mirror_lockup(0)
        
        # Should not have called mirror_lockup when delay is 0
        for camera_id in self.camera_manager.active_cameras:
            camera = self.camera_manager.cameras[camera_id]
            camera.mirror_lockup.assert_not_called()
    
    def test_get_execution_stats(self):
        """Test execution statistics retrieval."""
        # Simulate some executed actions
        self.scheduler.actions_executed = 3
        self.scheduler.photos_taken = 15
        self.scheduler.execution_errors = 1
        
        stats = self.scheduler.get_execution_stats()
        
        self.assertEqual(stats['actions_executed'], 3)
        self.assertEqual(stats['photos_taken'], 15)
        self.assertEqual(stats['execution_errors'], 1)
        self.assertTrue(stats['test_mode'])
    
    def test_reset_stats(self):
        """Test statistics reset."""
        # Set some stats
        self.scheduler.actions_executed = 5
        self.scheduler.photos_taken = 20
        self.scheduler.execution_errors = 2
        
        # Reset
        self.scheduler.reset_stats()
        
        self.assertEqual(self.scheduler.actions_executed, 0)
        self.assertEqual(self.scheduler.photos_taken, 0)
        self.assertEqual(self.scheduler.execution_errors, 0)
    
    def test_execute_action_with_validation_error(self):
        """Test action execution with invalid action config."""
        # Create invalid action (missing required fields)
        action = ActionConfig(
            action_type="Boucle",
            time_ref="C2",
            start_operator="+",
            start_time=time(0, 0, 0)
            # Missing end_time and interval_or_count
        )
        
        result = self.scheduler.execute_action(action)
        self.assertFalse(result)
        self.assertEqual(self.scheduler.execution_errors, 1)


if __name__ == '__main__':
    unittest.main()