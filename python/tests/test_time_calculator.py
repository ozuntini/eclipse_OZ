"""
Unit tests for time calculator.

Tests time conversion and calculation functions equivalent to the
original Magic Lantern Lua script.
"""

import unittest
from datetime import time
from unittest.mock import patch


from config.eclipse_config import EclipseTimings
from scheduling.time_calculator import TimeCalculator


class TestTimeCalculator(unittest.TestCase):
    """Test cases for TimeCalculator class."""
    
    def setUp(self):
        """Set up test fixtures with sample eclipse timings."""
        self.timings = EclipseTimings(
            c1=time(14, 41, 5),     # 14:41:05
            c2=time(16, 2, 49),     # 16:02:49  
            max=time(16, 3, 53),    # 16:03:53
            c3=time(16, 4, 58),     # 16:04:58
            c4=time(17, 31, 3),     # 17:31:03
            test_mode=False
        )
        self.calc = TimeCalculator(self.timings)
    
    def test_time_to_seconds(self):
        """Test conversion from time to seconds since midnight."""
        # Test basic conversions
        self.assertEqual(self.calc.time_to_seconds(time(0, 0, 0)), 0)
        self.assertEqual(self.calc.time_to_seconds(time(1, 0, 0)), 3600)
        self.assertEqual(self.calc.time_to_seconds(time(0, 1, 0)), 60)
        self.assertEqual(self.calc.time_to_seconds(time(0, 0, 1)), 1)
        
        # Test complex time
        self.assertEqual(self.calc.time_to_seconds(time(14, 41, 5)), 
                         14 * 3600 + 41 * 60 + 5)  # 52865 seconds
        
        # Test midnight
        self.assertEqual(self.calc.time_to_seconds(time(23, 59, 59)), 86399)
    
    def test_seconds_to_time(self):
        """Test conversion from seconds to time object."""
        # Test basic conversions
        self.assertEqual(self.calc.seconds_to_time(0), time(0, 0, 0))
        self.assertEqual(self.calc.seconds_to_time(3600), time(1, 0, 0))
        self.assertEqual(self.calc.seconds_to_time(60), time(0, 1, 0))
        self.assertEqual(self.calc.seconds_to_time(1), time(0, 0, 1))
        
        # Test complex time
        self.assertEqual(self.calc.seconds_to_time(52865), time(14, 41, 5))
        
        # Test day overflow
        self.assertEqual(self.calc.seconds_to_time(86400), time(0, 0, 0))  # Next day
        self.assertEqual(self.calc.seconds_to_time(90000), time(1, 0, 0))  # 25:00:00 -> 01:00:00
        
        # Test negative seconds (day underflow)
        self.assertEqual(self.calc.seconds_to_time(-3600), time(23, 0, 0))
    
    def test_bidirectional_conversion(self):
        """Test that time->seconds->time conversion is accurate."""
        test_times = [
            time(0, 0, 0),
            time(12, 30, 45),
            time(23, 59, 59),
            time(14, 41, 5),
            time(16, 3, 53)
        ]
        
        for test_time in test_times:
            seconds = self.calc.time_to_seconds(test_time)
            converted_back = self.calc.seconds_to_time(seconds)
            self.assertEqual(test_time, converted_back)
    
    def test_convert_relative_time_addition(self):
        """Test relative time calculations with addition."""
        # C2 + 00:01:00 = 16:02:49 + 00:01:00 = 16:03:49
        result = self.calc.convert_relative_time('C2', '+', time(0, 1, 0))
        expected = time(16, 3, 49)
        self.assertEqual(result, expected)
        
        # Max + 00:00:30 = 16:03:53 + 00:00:30 = 16:04:23
        result = self.calc.convert_relative_time('Max', '+', time(0, 0, 30))
        expected = time(16, 4, 23)
        self.assertEqual(result, expected)
    
    def test_convert_relative_time_subtraction(self):
        """Test relative time calculations with subtraction."""
        # C2 - 00:20:00 = 16:02:49 - 00:20:00 = 15:42:49
        result = self.calc.convert_relative_time('C2', '-', time(0, 20, 0))
        expected = time(15, 42, 49)
        self.assertEqual(result, expected)
        
        # C1 - 00:01:05 = 14:41:05 - 00:01:05 = 14:40:00
        result = self.calc.convert_relative_time('C1', '-', time(0, 1, 5))
        expected = time(14, 40, 0)
        self.assertEqual(result, expected)
    
    def test_convert_relative_time_day_crossing(self):
        """Test relative time calculations that cross day boundaries."""
        # C4 + 07:00:00 = 17:31:03 + 07:00:00 = 00:31:03 (next day)
        result = self.calc.convert_relative_time('C4', '+', time(7, 0, 0))
        expected = time(0, 31, 3)
        self.assertEqual(result, expected)
        
        # C1 - 15:00:00 = 14:41:05 - 15:00:00 = 23:41:05 (previous day)
        result = self.calc.convert_relative_time('C1', '-', time(15, 0, 0))
        expected = time(23, 41, 5)
        self.assertEqual(result, expected)
    
    def test_convert_relative_time_invalid_reference(self):
        """Test error handling for invalid time references."""
        with self.assertRaises(ValueError) as cm:
            self.calc.convert_relative_time('Invalid', '+', time(0, 1, 0))
        
        self.assertIn("Unknown time reference", str(cm.exception))
    
    def test_convert_relative_time_invalid_operator(self):
        """Test error handling for invalid operators."""
        with self.assertRaises(ValueError) as cm:
            self.calc.convert_relative_time('C1', '*', time(0, 1, 0))
        
        self.assertIn("Invalid operator", str(cm.exception))
    
    def test_get_time_difference(self):
        """Test time difference calculation."""
        # Same day difference
        time1 = time(14, 0, 0)
        time2 = time(15, 30, 0)
        diff = self.calc.get_time_difference(time1, time2)
        self.assertEqual(diff, 90 * 60)  # 1.5 hours = 5400 seconds
        
        # Cross-day difference
        time1 = time(23, 0, 0)
        time2 = time(1, 0, 0)  # Next day
        diff = self.calc.get_time_difference(time1, time2)
        self.assertEqual(diff, 2 * 3600)  # 2 hours
        
        # Zero difference
        time1 = time(12, 0, 0)
        time2 = time(12, 0, 0)
        diff = self.calc.get_time_difference(time1, time2)
        self.assertEqual(diff, 0)
    
    def test_format_duration(self):
        """Test duration formatting."""
        # Test various durations
        self.assertEqual(self.calc.format_duration(0), "0s")
        self.assertEqual(self.calc.format_duration(30), "30s")
        self.assertEqual(self.calc.format_duration(60), "1m")
        self.assertEqual(self.calc.format_duration(90), "1m 30s")
        self.assertEqual(self.calc.format_duration(3600), "1h")
        self.assertEqual(self.calc.format_duration(3661), "1h 1m 1s")
        
        # Test negative duration
        self.assertEqual(self.calc.format_duration(-30), "-30s")
    
    def test_validate_eclipse_sequence(self):
        """Test eclipse timing sequence validation."""
        # Valid sequence should pass
        self.assertTrue(self.calc.validate_eclipse_sequence())
        
        # Test with invalid sequence (C2 before C1)
        invalid_timings = EclipseTimings(
            c1=time(16, 0, 0),
            c2=time(15, 0, 0),  # Before C1 - invalid
            max=time(16, 3, 53),
            c3=time(16, 4, 58),
            c4=time(17, 31, 3),
            test_mode=False
        )
        invalid_calc = TimeCalculator(invalid_timings)
        self.assertFalse(invalid_calc.validate_eclipse_sequence())
    
    @patch('time.time')
    @patch('time.sleep')
    @patch('datetime.datetime')
    def test_wait_until(self, mock_datetime, mock_sleep, mock_time):
        """Test wait_until functionality."""
        # Mock current time progression
        mock_datetime.now.return_value.time.side_effect = [
            time(15, 59, 58),  # 2 seconds before target
            time(15, 59, 59),  # 1 second before target
            time(16, 0, 0),    # Target reached
        ]
        
        mock_time.side_effect = [100, 101, 102]  # For progress timing
        
        target_time = time(16, 0, 0)
        self.calc.wait_until(target_time, check_interval=0.1)
        
        # Should have called sleep at least once
        self.assertTrue(mock_sleep.called)
    
    def test_pre_calculated_references(self):
        """Test that reference times are pre-calculated correctly."""
        expected_refs = {
            'C1': self.calc.time_to_seconds(self.timings.c1),
            'C2': self.calc.time_to_seconds(self.timings.c2),
            'Max': self.calc.time_to_seconds(self.timings.max),
            'C3': self.calc.time_to_seconds(self.timings.c3),
            'C4': self.calc.time_to_seconds(self.timings.c4)
        }
        
        self.assertEqual(self.calc._ref_times_seconds, expected_refs)


if __name__ == '__main__':
    unittest.main()