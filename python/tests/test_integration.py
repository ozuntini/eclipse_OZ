"""
Integration tests for Eclipse Photography Controller.

Tests the complete system integration and workflow.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import time
from unittest.mock import patch, Mock

from config.config_parser import parse_config_file
from scheduling.time_calculator import TimeCalculator
from scheduling.action_scheduler import ActionScheduler

from hardware.multi_camera_manager import MultiCameraManager
from utils.validation import SystemValidator


class TestIntegration(unittest.TestCase):
    """Integration test cases for the complete system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create a complete test configuration file
        self.test_config = """# Eclipse Photography Configuration
# Test configuration for unit testing

Config,14:41:05,16:02:49,16:03:53,16:04:58,17:31:03,1

# Test photo actions
Photo,Max,-,00:00:10,-,-,-,-,-,4,1600,1,500
Photo,C2,+,00:00:30,-,-,-,-,-,5.6,800,0.5,0

# Test loop action
Boucle,C2,+,00:01:00,+,00:02:00,10,-,-,8,400,0.008,0

# Test interval action  
Interval,C3,-,00:01:00,+,00:02:00,5,-,-,11,200,0.004,1000
"""
        
        self.config_file = self.temp_dir / "test_eclipse.txt"
        with open(self.config_file, 'w') as f:
            f.write(self.test_config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_configuration_parsing(self):
        """Test complete configuration file parsing and validation."""
        # Parse configuration
        config = parse_config_file(str(self.config_file))
        
        # Validate structure
        self.assertIsNotNone(config.eclipse_timings)
        self.assertEqual(len(config.actions), 4)
        
        # Validate eclipse timings
        timings = config.eclipse_timings
        self.assertEqual(timings.c1, time(14, 41, 5))
        self.assertEqual(timings.c2, time(16, 2, 49))
        self.assertEqual(timings.max, time(16, 3, 53))
        self.assertEqual(timings.c3, time(16, 4, 58))
        self.assertEqual(timings.c4, time(17, 31, 3))
        self.assertTrue(timings.test_mode)
        
        # Validate actions
        actions = config.actions
        
        # Photo action 1 (Max - 10 seconds)
        self.assertEqual(actions[0].action_type, "Photo")
        self.assertEqual(actions[0].time_ref, "Max")
        self.assertEqual(actions[0].start_operator, "-")
        self.assertEqual(actions[0].start_time, time(0, 0, 10))
        
        # Photo action 2 (C2 + 30 seconds)
        self.assertEqual(actions[1].action_type, "Photo")
        self.assertEqual(actions[1].time_ref, "C2")
        self.assertEqual(actions[1].start_operator, "+")
        self.assertEqual(actions[1].start_time, time(0, 0, 30))
        
        # Loop action
        self.assertEqual(actions[2].action_type, "Boucle")
        self.assertEqual(actions[2].interval_or_count, 10.0)
        
        # Interval action
        self.assertEqual(actions[3].action_type, "Interval")
        self.assertEqual(actions[3].interval_or_count, 5.0)
    
    def test_time_calculation_integration(self):
        """Test time calculation with parsed configuration."""
        config = parse_config_file(str(self.config_file))
        calculator = TimeCalculator(config.eclipse_timings)
        
        # Test eclipse sequence validation
        self.assertTrue(calculator.validate_eclipse_sequence())
        
        # Test time calculations for each action
        for action in config.actions:
            if action.time_ref != '-':
                # Test relative time calculation
                if action.start_time:
                    calculated_time = calculator.convert_relative_time(
                        action.time_ref, action.start_operator, action.start_time
                    )
                    self.assertIsInstance(calculated_time, time)
                
                if hasattr(action, 'end_time') and action.end_time:
                    calculated_time = calculator.convert_relative_time(
                        action.time_ref, action.end_operator, action.end_time
                    )
                    self.assertIsInstance(calculated_time, time)
    
    def test_camera_manager_integration(self):
        """Test camera manager with mock cameras."""
        manager = MultiCameraManager()
        
        # Test camera discovery (mock implementation)
        cameras = manager.discover_cameras()
        self.assertIsInstance(cameras, list)
        
        if cameras:  # If mock cameras were discovered
            # Test camera information
            info = manager.get_camera_info()
            self.assertIsInstance(info, dict)
            
            # Test status retrieval
            status = manager.get_all_status()
            self.assertIsInstance(status, dict)
            
            # Test configuration
            from config.eclipse_config import CameraSettings
            settings = CameraSettings(iso=1600, aperture="f/8", shutter="1/125")
            results = manager.configure_all(settings)
            self.assertIsInstance(results, dict)
            
            # Test capture
            capture_results = manager.capture_all(test_mode=True)
            self.assertIsInstance(capture_results, dict)
            
            # Clean up
            manager.disconnect_all()
    
    def test_scheduler_integration(self):
        """Test action scheduler with complete workflow."""
        # Parse configuration
        config = parse_config_file(str(self.config_file))
        
        # Create time calculator
        calculator = TimeCalculator(config.eclipse_timings)
        
        # Create mock camera manager
        camera_manager = Mock(spec=MultiCameraManager)
        camera_manager.active_cameras = [0]
        camera_manager.cameras = {0: Mock()}
        camera_manager.configure_all.return_value = {0: True}
        camera_manager.capture_all.return_value = {0: "test_image.jpg"}
        
        # Create scheduler
        scheduler = ActionScheduler(camera_manager, calculator, test_mode=True)
        
        # Test action execution with mocked time
        with patch.object(calculator, 'wait_until'):
            # Test each action type
            for action in config.actions:
                result = scheduler.execute_action(action)
                # Should succeed in test mode
                self.assertTrue(result, f"Action {action.action_type} failed")
        
        # Check execution statistics
        stats = scheduler.get_execution_stats()
        self.assertEqual(stats['actions_executed'], len(config.actions))
        self.assertGreater(stats['photos_taken'], 0)
        self.assertEqual(stats['execution_errors'], 0)
    
    def test_system_validation_integration(self):
        """Test system validation with complete configuration."""
        # Parse configuration
        config = parse_config_file(str(self.config_file))
        
        # Create validator
        validator = SystemValidator()
        
        # Test configuration validation
        result = validator.validate_configuration(config)
        # Should pass with valid test configuration
        self.assertTrue(result)
        
        # Test system validation (may fail in test environment)
        system_result = validator.validate_system()
        # Don't assert on system validation as it depends on environment
        self.assertIsInstance(system_result, bool)
    
    def test_error_handling_integration(self):
        """Test error handling throughout the system."""
        # Test with invalid configuration file
        invalid_config = """# Invalid configuration
Config,invalid_time,16:02:49,16:03:53,16:04:58,17:31:03,1
"""
        
        invalid_file = self.temp_dir / "invalid.txt"
        with open(invalid_file, 'w') as f:
            f.write(invalid_config)
        
        # Should raise ConfigParserError
        with self.assertRaises(Exception):
            parse_config_file(str(invalid_file))
    
    def test_full_workflow_simulation(self):
        """Test a complete workflow simulation."""
        # Parse configuration
        config = parse_config_file(str(self.config_file))
        
        # Create components
        calculator = TimeCalculator(config.eclipse_timings)
        validator = SystemValidator()
        
        # Mock camera manager for full workflow
        camera_manager = Mock(spec=MultiCameraManager)
        camera_manager.discover_cameras.return_value = [0, 1]
        camera_manager.active_cameras = [0, 1]
        camera_manager.get_all_status.return_value = {
            0: Mock(connected=True, battery_level=85),
            1: Mock(connected=True, battery_level=90)
        }
        camera_manager.configure_all.return_value = {0: True, 1: True}
        camera_manager.capture_all.return_value = {0: "img1.jpg", 1: "img2.jpg"}
        camera_manager.validate_all_cameras.return_value = True
        
        # Create scheduler
        scheduler = ActionScheduler(camera_manager, calculator, test_mode=True)
        
        # Simulate full workflow
        try:
            # 1. Validate configuration
            self.assertTrue(validator.validate_configuration(config))
            
            # 2. Initialize cameras
            cameras = camera_manager.discover_cameras()
            self.assertEqual(len(cameras), 2)
            
            # 3. Validate cameras
            self.assertTrue(camera_manager.validate_all_cameras())
            
            # 4. Execute actions
            with patch.object(calculator, 'wait_until'):
                for i, action in enumerate(config.actions):
                    result = scheduler.execute_action(action)
                    self.assertTrue(result, f"Action {i+1} failed")
            
            # 5. Check final statistics
            stats = scheduler.get_execution_stats()
            self.assertEqual(stats['actions_executed'], 4)
            self.assertTrue(stats['photos_taken'] > 0)
            self.assertEqual(stats['execution_errors'], 0)
            
        finally:
            # 6. Cleanup
            camera_manager.disconnect_all()
    
    def test_timing_precision_simulation(self):
        """Test timing precision with rapid succession actions."""
        # Create configuration with rapid actions
        rapid_config = """Config,16:00:00,16:00:30,16:01:00,16:01:30,16:02:00,1
Photo,Max,-,00:00:01,-,-,-,-,-,8,1600,0.008,0
Photo,Max,+,00:00:01,-,-,-,-,-,8,1600,0.008,0
Photo,Max,+,00:00:02,-,-,-,-,-,8,1600,0.008,0
"""
        
        rapid_file = self.temp_dir / "rapid.txt"
        with open(rapid_file, 'w') as f:
            f.write(rapid_config)
        
        # Parse and test
        config = parse_config_file(str(rapid_file))
        calculator = TimeCalculator(config.eclipse_timings)
        
        # Calculate timing for each action
        times = []
        for action in config.actions:
            if action.time_ref != '-':
                calc_time = calculator.convert_relative_time(
                    action.time_ref, action.start_operator, action.start_time
                )
                times.append(calc_time)
        
        # Check that times are in correct sequence
        for i in range(len(times) - 1):
            time1_seconds = calculator.time_to_seconds(times[i])
            time2_seconds = calculator.time_to_seconds(times[i + 1])
            self.assertLess(time1_seconds, time2_seconds, 
                          f"Action {i+1} time >= Action {i+2} time")


if __name__ == '__main__':
    unittest.main()