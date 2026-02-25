"""
Multi-camera manager for Eclipse Photography Controller.

Manages multiple camera connections and provides synchronized operations
across all connected cameras.
"""

import threading
import logging
from typing import Dict, List, Optional, Tuple
import time

# Import with fallback for development
try:
    import gphoto2 as gp
    GPHOTO2_AVAILABLE = True
except ImportError:
    GPHOTO2_AVAILABLE = False
    # Use mock from camera_controller
    from .camera_controller import gp

from .camera_controller import CameraController
from ..config.eclipse_config import CameraSettings, CameraStatus


class MultiCameraManager:
    """
    Manager for multiple camera controllers.
    
    Provides:
    - Automatic camera detection
    - Synchronized configuration
    - Parallel capture operations
    - Error isolation per camera
    """
    
    def __init__(self):
        self.cameras: Dict[int, CameraController] = {}
        self.active_cameras: List[int] = []
        self.logger = logging.getLogger('multi_camera_manager')
        
        # Thread safety for parallel operations
        self._operation_lock = threading.Lock()
        
    def discover_cameras(self) -> List[int]:
        """
        Discover and connect to all available cameras.
        
        Returns:
            List of camera IDs that were successfully connected
        """
        self.logger.info("Discovering cameras...")
        
        try:
            if not GPHOTO2_AVAILABLE:
                # Mock discovery for development
                self.logger.info("Mock camera discovery")
                camera_list = [("Mock Canon Camera 1", "usb:001,002"),
                              ("Mock Canon Camera 2", "usb:001,003")]
            else:
                camera_list = gp.gp_camera_autodetect()
            
            discovered_cameras = []
            
            for index, (name, address) in enumerate(camera_list):
                self.logger.info(f"Found camera {index}: {name} at {address}")
                
                # Create controller and attempt connection
                controller = CameraController(index, name)
                
                if controller.connect(address):
                    self.cameras[index] = controller
                    discovered_cameras.append(index)
                    self.logger.info(f"Camera {index} connected successfully")
                else:
                    self.logger.warning(f"Failed to connect to camera {index}")
            
            self.active_cameras = discovered_cameras
            self.logger.info(f"Discovery complete: {len(discovered_cameras)} cameras available")
            
            return discovered_cameras
            
        except Exception as e:
            self.logger.error(f"Error during camera discovery: {e}")
            return []
    
    def get_camera_count(self) -> int:
        """Get number of active cameras."""
        return len(self.active_cameras)
    
    def get_camera_names(self) -> Dict[int, str]:
        """Get mapping of camera IDs to names."""
        return {cid: self.cameras[cid].name for cid in self.active_cameras}
    
    def configure_all(self, settings: CameraSettings) -> Dict[int, bool]:
        """
        Configure all active cameras with the same settings.
        
        Args:
            settings: Camera settings to apply
            
        Returns:
            Dictionary mapping camera ID to success status
        """
        self.logger.info(f"Configuring all cameras: ISO {settings.iso}, "
                        f"{settings.aperture}, {settings.shutter}")
        
        results = {}
        
        for camera_id in self.active_cameras:
            try:
                success = self.cameras[camera_id].configure_settings(settings)
                results[camera_id] = success
                
                if not success:
                    self.logger.warning(f"Configuration failed for camera {camera_id}")
            
            except Exception as e:
                self.logger.error(f"Error configuring camera {camera_id}: {e}")
                results[camera_id] = False
        
        successful_configs = sum(1 for success in results.values() if success)
        self.logger.info(f"Configuration complete: {successful_configs}/{len(results)} successful")
        
        return results
    
    def configure_individual(self, camera_id: int, settings: CameraSettings) -> bool:
        """
        Configure a specific camera.
        
        Args:
            camera_id: ID of camera to configure
            settings: Camera settings to apply
            
        Returns:
            True if successful, False otherwise
        """
        if camera_id not in self.active_cameras:
            self.logger.error(f"Camera {camera_id} not available")
            return False
        
        return self.cameras[camera_id].configure_settings(settings)
    
    def capture_all(self, test_mode: bool = False) -> Dict[int, Optional[str]]:
        """
        Capture photos with all cameras simultaneously.
        
        Uses threading for parallel capture to minimize timing differences.
        
        Args:
            test_mode: If True, simulate captures
            
        Returns:
            Dictionary mapping camera ID to captured file path (or None if failed)
        """
        self.logger.info(f"Capturing with all cameras (test_mode={test_mode})")
        
        results = {}
        threads = []
        
        # Capture start time for synchronization
        capture_start_time = time.time()
        
        def capture_single_camera(camera_id: int):
            """Capture function for individual camera thread."""
            try:
                # Small delay to synchronize start times
                sleep_time = 0.1 - (time.time() - capture_start_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                result = self.cameras[camera_id].capture_image(test_mode)
                
                with self._operation_lock:
                    results[camera_id] = result
                    
            except Exception as e:
                self.logger.error(f"Error capturing with camera {camera_id}: {e}")
                with self._operation_lock:
                    results[camera_id] = None
        
        # Start capture threads
        for camera_id in self.active_cameras:
            thread = threading.Thread(
                target=capture_single_camera,
                args=(camera_id,),
                name=f"Capture_Camera_{camera_id}"
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all captures to complete
        for thread in threads:
            thread.join(timeout=30.0)  # 30 second timeout per capture
            
            if thread.is_alive():
                self.logger.warning(f"Capture thread {thread.name} timed out")
        
        # Log results
        successful_captures = sum(1 for result in results.values() if result is not None)
        self.logger.info(f"Capture complete: {successful_captures}/{len(results)} successful")
        
        for camera_id, result in results.items():
            if result:
                self.logger.info(f"Camera {camera_id}: {result}")
            else:
                self.logger.error(f"Camera {camera_id}: Capture failed")
        
        return results
    
    def capture_sequence(self, count: int, interval: float, test_mode: bool = False) -> List[Dict[int, Optional[str]]]:
        """
        Capture a sequence of photos with all cameras.
        
        Args:
            count: Number of photos to take
            interval: Interval between photos in seconds
            test_mode: If True, simulate captures
            
        Returns:
            List of capture results, one per sequence step
        """
        self.logger.info(f"Starting sequence: {count} photos, {interval}s interval")
        
        sequence_results = []
        
        for i in range(count):
            self.logger.info(f"Sequence step {i + 1}/{count}")
            
            # Capture with all cameras
            capture_result = self.capture_all(test_mode)
            sequence_results.append(capture_result)
            
            # Wait for interval (except on last capture)
            if i < count - 1:
                time.sleep(interval)
        
        self.logger.info("Sequence complete")
        return sequence_results
    
    def get_all_status(self) -> Dict[int, CameraStatus]:
        """
        Get status of all active cameras.
        
        Returns:
            Dictionary mapping camera ID to status
        """
        status_dict = {}
        
        for camera_id in self.active_cameras:
            try:
                status = self.cameras[camera_id].get_status()
                status_dict[camera_id] = status
            except Exception as e:
                self.logger.error(f"Error getting status for camera {camera_id}: {e}")
                status_dict[camera_id] = CameraStatus(connected=False, last_error=str(e))
        
        return status_dict
    
    def validate_all_cameras(self) -> bool:
        """
        Validate that all cameras are ready for photography.
        
        Returns:
            True if all cameras are ready, False otherwise
        """
        self.logger.info("Validating all cameras...")
        
        all_status = self.get_all_status()
        all_ready = True
        
        for camera_id, status in all_status.items():
            camera_name = self.cameras[camera_id].name
            
            if not status.connected:
                self.logger.error(f"{camera_name}: Not connected")
                all_ready = False
                continue
            
            # Check battery level
            if status.battery_level is not None and status.battery_level < 20:
                self.logger.warning(f"{camera_name}: Low battery ({status.battery_level}%)")
                # Don't fail for low battery, just warn
            
            # Check free space
            if status.free_space_mb is not None and status.free_space_mb < 100:
                self.logger.warning(f"{camera_name}: Low storage space ({status.free_space_mb}MB)")
            
            # Log status
            self.logger.info(f"{camera_name}: Mode={status.mode}, "
                           f"AF={'On' if status.af_enabled else 'Off'}, "
                           f"Battery={status.battery_level}%")
        
        if all_ready:
            self.logger.info("All cameras validated successfully")
        else:
            self.logger.error("Camera validation failed")
        
        return all_ready
    
    def disconnect_all(self):
        """Disconnect all cameras cleanly."""
        self.logger.info("Disconnecting all cameras...")
        
        for camera_id, controller in self.cameras.items():
            try:
                controller.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting camera {camera_id}: {e}")
        
        self.cameras.clear()
        self.active_cameras.clear()
        
        self.logger.info("All cameras disconnected")
    
    def remove_camera(self, camera_id: int):
        """
        Remove a specific camera from management.
        
        Args:
            camera_id: ID of camera to remove
        """
        if camera_id in self.cameras:
            try:
                self.cameras[camera_id].disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting camera {camera_id}: {e}")
            
            del self.cameras[camera_id]
            
            if camera_id in self.active_cameras:
                self.active_cameras.remove(camera_id)
            
            self.logger.info(f"Camera {camera_id} removed")
    
    def set_active_cameras(self, camera_ids: List[int]):
        """
        Set which cameras should be used for operations.
        
        Args:
            camera_ids: List of camera IDs to use
        """
        # Validate that all specified cameras exist
        available_cameras = set(self.cameras.keys())
        requested_cameras = set(camera_ids)
        
        if not requested_cameras.issubset(available_cameras):
            missing = requested_cameras - available_cameras
            raise ValueError(f"Cameras not available: {missing}")
        
        self.active_cameras = camera_ids
        self.logger.info(f"Active cameras set to: {camera_ids}")
    
    def get_camera_info(self) -> Dict[int, Dict[str, Any]]:
        """
        Get detailed information about all cameras.
        
        Returns:
            Dictionary with camera info
        """
        info = {}
        
        for camera_id in self.cameras:
            controller = self.cameras[camera_id]
            status = controller.get_status()
            
            info[camera_id] = {
                'name': controller.name,
                'connected': status.connected,
                'active': camera_id in self.active_cameras,
                'status': status
            }
        
        return info