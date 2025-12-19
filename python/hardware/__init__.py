"""Hardware module package initialization."""

from .camera_controller import CameraController
from .multi_camera_manager import MultiCameraManager

__all__ = ['CameraController', 'MultiCameraManager']