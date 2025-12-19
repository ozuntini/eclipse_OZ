"""Test module package initialization."""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test modules
from .test_config_parser import TestConfigParser
from .test_time_calculator import TestTimeCalculator
from .test_camera_controller import TestCameraController
from .test_action_scheduler import TestActionScheduler
from .test_integration import TestIntegration

__all__ = [
    'TestConfigParser', 
    'TestTimeCalculator', 
    'TestCameraController',
    'TestActionScheduler',
    'TestIntegration'
]


def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestConfigParser))
    suite.addTests(loader.loadTestsFromTestCase(TestTimeCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestCameraController))
    suite.addTests(loader.loadTestsFromTestCase(TestActionScheduler))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_all_tests()