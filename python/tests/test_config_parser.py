"""
Unit tests for configuration parser.

Tests the parsing and validation of eclipse configuration files.
"""

import unittest
import tempfile
import os
from datetime import time
from pathlib import Path

from config.config_parser import ConfigParser, ConfigParserError
from config.eclipse_config import EclipseTimings, ActionConfig


class TestConfigParser(unittest.TestCase):
    """Test cases for ConfigParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = ConfigParser()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_temp_config(self, content: str) -> str:
        """Create temporary config file with given content."""
        config_file = self.temp_dir / "test_config.txt"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return str(config_file)
    
    def test_parse_valid_config(self):
        """Test parsing a valid configuration file."""
        content = """# Test eclipse configuration
Config,14:41:05,16:02:49,16:03:53,16:04:58,17:31:03,1
Photo,Max,-,00:00:10,-,-,-,-,-,4,1600,1,500
Boucle,C2,+,00:00:00,-,00:01:00,2,-,-,5.6,800,0.008,0
Interval,C3,-,00:00:30,+,00:02:00,5,-,-,8,400,0.004,1000
"""
        
        config_file = self._create_temp_config(content)
        config = self.parser.parse_eclipse_config(config_file)
        
        # Check eclipse timings
        self.assertEqual(config.eclipse_timings.c1, time(14, 41, 5))
        self.assertEqual(config.eclipse_timings.c2, time(16, 2, 49))
        self.assertEqual(config.eclipse_timings.max, time(16, 3, 53))
        self.assertEqual(config.eclipse_timings.c3, time(16, 4, 58))
        self.assertEqual(config.eclipse_timings.c4, time(17, 31, 3))
        self.assertTrue(config.eclipse_timings.test_mode)
        
        # Check actions
        self.assertEqual(len(config.actions), 3)
        
        # Check Photo action
        photo_action = config.actions[0]
        self.assertEqual(photo_action.action_type, "Photo")
        self.assertEqual(photo_action.time_ref, "Max")
        self.assertEqual(photo_action.start_operator, "-")
        self.assertEqual(photo_action.start_time, time(0, 0, 10))
        self.assertEqual(photo_action.aperture, 4.0)
        self.assertEqual(photo_action.iso, 1600)
        self.assertEqual(photo_action.shutter_speed, 1.0)
        self.assertEqual(photo_action.mlu_delay, 500)
        
        # Check Boucle action
        boucle_action = config.actions[1]
        self.assertEqual(boucle_action.action_type, "Boucle")
        self.assertEqual(boucle_action.time_ref, "C2")
        self.assertEqual(boucle_action.start_operator, "+")
        self.assertEqual(boucle_action.end_operator, "-")
        self.assertEqual(boucle_action.interval_or_count, 2.0)
        
        # Check Interval action
        interval_action = config.actions[2]
        self.assertEqual(interval_action.action_type, "Interval")
        self.assertEqual(interval_action.interval_or_count, 5.0)
        self.assertEqual(interval_action.mlu_delay, 1000)
    
    def test_parse_time_string(self):
        """Test time string parsing."""
        # Valid times
        self.assertEqual(self.parser._parse_time_string("14:30:15", 1), time(14, 30, 15))
        self.assertEqual(self.parser._parse_time_string("00:00:00", 1), time(0, 0, 0))
        self.assertEqual(self.parser._parse_time_string("23:59:59", 1), time(23, 59, 59))
        
        # Invalid times
        with self.assertRaises(ConfigParserError):
            self.parser._parse_time_string("25:00:00", 1)
        
        with self.assertRaises(ConfigParserError):
            self.parser._parse_time_string("12:60:00", 1)
        
        with self.assertRaises(ConfigParserError):
            self.parser._parse_time_string("12:30:60", 1)
        
        with self.assertRaises(ConfigParserError):
            self.parser._parse_time_string("invalid", 1)
    
    def test_missing_config_line(self):
        """Test error when Config line is missing."""
        content = """Photo,Max,-,00:00:10,-,-,-,-,-,4,1600,1,500"""
        
        config_file = self._create_temp_config(content)
        
        with self.assertRaises(ConfigParserError) as cm:
            self.parser.parse_eclipse_config(config_file)
        
        self.assertIn("Missing required 'Config' line", str(cm.exception))
    
    def test_no_actions(self):
        """Test error when no actions are defined."""
        content = """Config,14:41:05,16:02:49,16:03:53,16:04:58,17:31:03,0"""
        
        config_file = self._create_temp_config(content)
        
        with self.assertRaises(ConfigParserError) as cm:
            self.parser.parse_eclipse_config(config_file)
        
        self.assertIn("No photo actions defined", str(cm.exception))
    
    def test_invalid_config_fields(self):
        """Test error handling for invalid Config line."""
        # Too few fields
        content = """Config,14:41:05,16:02:49"""
        
        config_file = self._create_temp_config(content)
        
        with self.assertRaises(ConfigParserError):
            self.parser.parse_eclipse_config(config_file)
    
    def test_invalid_action_fields(self):
        """Test error handling for invalid action lines."""
        content = """Config,14:41:05,16:02:49,16:03:53,16:04:58,17:31:03,0
Photo,Max"""  # Too few fields
        
        config_file = self._create_temp_config(content)
        
        with self.assertRaises(ConfigParserError):
            self.parser.parse_eclipse_config(config_file)
    
    def test_invalid_time_reference(self):
        """Test error handling for invalid time references."""
        content = """Config,14:41:05,16:02:49,16:03:53,16:04:58,17:31:03,0
Photo,Invalid,-,00:00:10,-,-,-,-,-,4,1600,1,500"""
        
        config_file = self._create_temp_config(content)
        
        with self.assertRaises(ConfigParserError) as cm:
            self.parser.parse_eclipse_config(config_file)
        
        self.assertIn("Invalid time reference", str(cm.exception))
    
    def test_comments_and_empty_lines(self):
        """Test that comments and empty lines are ignored."""
        content = """# This is a comment
Config,14:41:05,16:02:49,16:03:53,16:04:58,17:31:03,0

# Another comment
Photo,Max,-,00:00:10,-,-,-,-,-,4,1600,1,500

"""
        
        config_file = self._create_temp_config(content)
        config = self.parser.parse_eclipse_config(config_file)
        
        self.assertIsNotNone(config.eclipse_timings)
        self.assertEqual(len(config.actions), 1)
    
    def test_split_config_line(self):
        """Test configuration line splitting."""
        # Test basic comma splitting
        line = "Config,14:41:05,16:02:49,test"
        fields = self.parser._split_config_line(line)
        expected = ["Config", "14:41:05", "16:02:49", "test"]
        self.assertEqual(fields, expected)
        
        # Test with extra spaces
        line = "Config, 14:41:05 , 16:02:49, test "
        fields = self.parser._split_config_line(line)
        expected = ["Config", "14:41:05", "16:02:49", "test"]
        self.assertEqual(fields, expected)
    
    def test_file_not_found(self):
        """Test error when configuration file doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.parser.parse_eclipse_config("nonexistent_file.txt")
    
    def test_unicode_handling(self):
        """Test handling of unicode characters in config."""
        content = """# Configuration éclipse
Config,14:41:05,16:02:49,16:03:53,16:04:58,17:31:03,0
Photo,Max,-,00:00:10,-,-,-,-,-,4,1600,1,500
"""
        
        config_file = self._create_temp_config(content)
        config = self.parser.parse_eclipse_config(config_file)
        
        self.assertIsNotNone(config)
        self.assertEqual(len(config.actions), 1)


if __name__ == '__main__':
    unittest.main()