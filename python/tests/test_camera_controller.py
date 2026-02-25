"""
Unit tests for camera controller.

Tests camera connection, configuration, and capture functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import time

from config.eclipse_config import CameraSettings, CameraStatus
from hardware.camera_controller import CameraController, format_gphoto2_aperture, format_gphoto2_shutter


class TestCameraController(unittest.TestCase):
    """Test cases for CameraController class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.camera_id = 0
        self.camera_name = "Test Camera"
        self.controller = CameraController(self.camera_id, self.camera_name)
    
    def test_initialization(self):
        """Test camera controller initialization."""
        self.assertEqual(self.controller.camera_id, self.camera_id)
        self.assertEqual(self.controller.name, self.camera_name)
        self.assertIsNone(self.controller.camera)
        self.assertFalse(self.controller.connected)
    
    def test_connect_success(self):
        """Test successful camera connection."""
        # Since gphoto2 may not be available in test environment,
        # this tests the mock path
        result = self.controller.connect()
        
        # Should succeed with mock implementation
        self.assertTrue(result)
        self.assertTrue(self.controller.connected)
    
    def test_disconnect(self):
        """Test camera disconnection."""
        # Connect first
        self.controller.connect()
        self.assertTrue(self.controller.connected)
        
        # Disconnect
        self.controller.disconnect()
        self.assertFalse(self.controller.connected)
        self.assertIsNone(self.controller.camera)
    
    def test_get_status_not_connected(self):
        """Test get_status when not connected."""
        status = self.controller.get_status()
        
        self.assertFalse(status.connected)
        self.assertEqual(status.last_error, "Not connected")
    
    def test_get_status_connected(self):
        """Test get_status when connected."""
        # Connect camera
        self.controller.connect()
        
        status = self.controller.get_status()
        
        self.assertTrue(status.connected)
        # Mock implementation should return some values
        self.assertIsNotNone(status)
    
    def test_configure_settings_not_connected(self):
        """Test configure_settings when not connected."""
        settings = CameraSettings(
            iso=1600,
            aperture="f/8",
            shutter="1/125"
        )
        
        result = self.controller.configure_settings(settings)
        self.assertFalse(result)
    
    def test_configure_settings_connected(self):
        """Test configure_settings when connected."""
        # Connect camera
        self.controller.connect()
        
        settings = CameraSettings(
            iso=1600,
            aperture="f/8", 
            shutter="1/125"
        )
        
        result = self.controller.configure_settings(settings)
        # Should succeed with mock implementation
        self.assertTrue(result)
    
    def test_capture_image_test_mode(self):
        """Test capture_image in test mode."""
        result = self.controller.capture_image(test_mode=True)
        
        # Should return a test filename
        self.assertIsNotNone(result)
        self.assertIn("test_image", result)
        self.assertIn(str(self.camera_id), result)
    
    def test_capture_image_not_connected(self):
        """Test capture_image when not connected."""
        result = self.controller.capture_image(test_mode=False)
        self.assertIsNone(result)
    
    def test_capture_image_connected(self):
        """Test capture_image when connected."""
        # Connect camera
        self.controller.connect()
        
        result = self.controller.capture_image(test_mode=False)
        
        # Should succeed with mock implementation
        self.assertIsNotNone(result)
    
    def test_mirror_lockup(self):
        """Test mirror lockup configuration."""
        # Connect camera
        self.controller.connect()
        
        # Test enabling mirror lockup
        result = self.controller.mirror_lockup(True, 500)
        self.assertTrue(result)
        
        # Test disabling mirror lockup
        result = self.controller.mirror_lockup(False, 0)
        self.assertTrue(result)
    
    def test_format_gphoto2_aperture(self):
        """Test aperture formatting for GPhoto2."""
        # Test integer apertures
        self.assertEqual(format_gphoto2_aperture(8.0), "f/8")
        self.assertEqual(format_gphoto2_aperture(11.0), "f/11")
        
        # Test fractional apertures
        self.assertEqual(format_gphoto2_aperture(5.6), "f/5.6")
        self.assertEqual(format_gphoto2_aperture(2.8), "f/2.8")
    
    def test_format_gphoto2_shutter(self):
        """Test shutter speed formatting for GPhoto2."""
        # Test slow shutter speeds (>= 1 second)
        self.assertEqual(format_gphoto2_shutter(1.0), "1")
        self.assertEqual(format_gphoto2_shutter(2.0), "2")
        self.assertEqual(format_gphoto2_shutter(2.5), "2.5")
        
        # Test fast shutter speeds (< 1 second)
        self.assertEqual(format_gphoto2_shutter(0.008), "1/125")  # 1/125 second
        self.assertEqual(format_gphoto2_shutter(0.004), "1/250")  # 1/250 second
        self.assertEqual(format_gphoto2_shutter(0.001), "1/1000") # 1/1000 second
        
        # Test common fractions
        self.assertEqual(format_gphoto2_shutter(1/60), "1/60")
        self.assertEqual(format_gphoto2_shutter(1/125), "1/125")
        self.assertEqual(format_gphoto2_shutter(1/250), "1/250")
    
    def test_get_config_value_mock(self):
        """Test _get_config_value with mock values."""
        self.controller.connect()
        
        # Test string value
        result = self.controller._get_config_value("mock_config", "capturetarget", str)
        self.assertEqual(result, "Memory card")
        
        # Test integer value
        result = self.controller._get_config_value("mock_config", "batterylevel", int)
        self.assertEqual(result, 85)
        
        # Test non-existent value
        result = self.controller._get_config_value("mock_config", "nonexistent", str)
        self.assertIsNone(result)
    
    def test_set_config_value_mock(self):
        """Test _set_config_value with mock implementation."""
        self.controller.connect()
        
        # Should succeed with mock implementation
        result = self.controller._set_config_value("mock_config", "iso", "1600")
        self.assertTrue(result)
        
        result = self.controller._set_config_value("mock_config", "aperture", "f/8")
        self.assertTrue(result)
    
    def test_camera_name_default(self):
        """Test default camera name generation."""
        controller = CameraController(5)
        self.assertEqual(controller.name, "Camera_5")
    
    def test_capabilities_cache_initialization(self):
        """Test that capabilities cache is properly initialized."""
        self.assertIsInstance(self.controller._capabilities_cache, dict)
        self.assertIsInstance(self.controller._config_cache, dict)
        self.assertEqual(len(self.controller._capabilities_cache), 0)
        self.assertEqual(len(self.controller._config_cache), 0)


class TestCameraControllerWithRealGPhoto2(unittest.TestCase):
    """
    Test cases that would run with real GPhoto2 if available.
    
    These tests are designed to be skipped if GPhoto2 is not available
    but provide a framework for testing with real hardware.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            import gphoto2
            self.gphoto2_available = True
        except ImportError:
            self.gphoto2_available = False
        
        self.controller = CameraController(0, "Real Camera Test")
    
    @unittest.skipUnless(False, "Real GPhoto2 tests disabled by default")
    def test_real_camera_detection(self):
        """Test real camera detection and connection."""
        if not self.gphoto2_available:
            self.skipTest("GPhoto2 not available")
        
        # This would test with real hardware
        # Only enable when testing with actual cameras
        result = self.controller.connect()
        
        if result:
            # Test basic operations
            status = self.controller.get_status()
            self.assertTrue(status.connected)
            
            # Test configuration
            settings = CameraSettings(iso=800, aperture="f/8", shutter="1/60")
            config_result = self.controller.configure_settings(settings)
            
            # Test capture in test mode
            capture_result = self.controller.capture_image(test_mode=True)
            self.assertIsNotNone(capture_result)
            
            # Clean up
            self.controller.disconnect()
        else:
            self.skipTest("No real camera available for testing")


if __name__ == '__main__':
    unittest.main()