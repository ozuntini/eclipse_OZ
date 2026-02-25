#!/usr/bin/env python3
"""
Eclipse Photography Controller - Main Entry Point

Python/GPhoto2 migration of the Magic Lantern eclipse_OZ.lua script.
Provides automated eclipse photography with multi-camera support.

Usage:
    python main.py config_eclipse.txt [options]
    python main.py config_eclipse.txt --test-mode --log-level DEBUG
    python main.py config_eclipse.txt --cameras 0 1 2 --log-file eclipse.log
"""

import argparse
import sys
import signal
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Import application modules
from config import ConfigParser, parse_config_file
from config.eclipse_config import SystemConfig
from hardware import MultiCameraManager, CameraController
from scheduling import TimeCalculator, ActionScheduler
from utils import setup_logging, SystemValidator
from utils.constants import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION, 
    ERROR_MESSAGES, SUCCESS_MESSAGES
)


class EclipsePhotographyController:
    """Main application controller."""
    
    def __init__(self, config_file: str, **options):
        """
        Initialize the eclipse photography controller.
        
        Args:
            config_file: Path to configuration file
            **options: Additional options (test_mode, log_level, cameras, etc.)
        """
        self.config_file = config_file
        self.options = options
        self.logger = None
        
        # Core components
        self.config: Optional[SystemConfig] = None
        self.camera_manager: Optional[MultiCameraManager] = None
        self.time_calculator: Optional[TimeCalculator] = None
        self.scheduler: Optional[ActionScheduler] = None
        self.validator: Optional[SystemValidator] = None
        
        # Runtime state
        self.is_running = False
        self.shutdown_requested = False
        
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Setup logging
            log_file = self.options.get('log_file', 'eclipse_oz.log')
            log_level = self.options.get('log_level', 'INFO')
            
            self.logger = setup_logging(log_level, log_file)
            self.logger.info(f"=== {APP_NAME} v{APP_VERSION} ===")
            self.logger.info(f"Initializing with config: {self.config_file}")
            
            # Parse configuration
            self.logger.info("Loading configuration...")
            self.config = parse_config_file(self.config_file)
            
            # Override test mode if specified
            if self.options.get('test_mode', False):
                self.config.test_mode = True
                
            self.logger.info(f"Configuration loaded: {len(self.config.actions)} actions")
            self.logger.info(f"Test mode: {'ENABLED' if self.config.test_mode else 'DISABLED'}")
            
            # Initialize system validator
            self.validator = SystemValidator()
            
            # Validate system
            if not self.validator.validate_system():
                self.logger.error("System validation failed")
                return False
                
            # Validate configuration
            if not self.validator.validate_configuration(self.config):
                self.logger.error("Configuration validation failed")
                return False
            
            # Initialize camera manager
            self.logger.info("Initializing camera system...")
            self.camera_manager = MultiCameraManager()
            
            # Discover cameras
            detected_cameras = self.camera_manager.discover_cameras()
            
            if not detected_cameras:
                self.logger.error(ERROR_MESSAGES['no_cameras'])
                return False
            
            self.logger.info(f"Cameras detected: {detected_cameras}")
            
            # Set active cameras if specified
            if 'cameras' in self.options:
                specified_cameras = self.options['cameras']
                available_cameras = set(detected_cameras)
                requested_cameras = set(specified_cameras)
                
                if not requested_cameras.issubset(available_cameras):
                    missing = requested_cameras - available_cameras
                    self.logger.error(f"Requested cameras not available: {missing}")
                    return False
                
                self.camera_manager.set_active_cameras(specified_cameras)
                self.logger.info(f"Active cameras: {specified_cameras}")
            
            # Validate cameras if verification is configured
            if self.config.verification:
                if not self.validator.validate_cameras(self.camera_manager, self.config.verification):
                    self.logger.error("Camera validation failed")
                    return False
            
            # Initialize time calculator
            self.time_calculator = TimeCalculator(self.config.eclipse_timings)
            
            # Initialize action scheduler
            self.scheduler = ActionScheduler(
                self.camera_manager, 
                self.time_calculator, 
                self.config.test_mode
            )
            
            self.logger.info("Initialization complete")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Initialization failed: {e}", exc_info=True)
            else:
                print(f"Initialization failed: {e}")
            return False
    
    def run(self) -> int:
        """
        Run the eclipse photography sequence.
        
        Returns:
            Exit code (0 for success, 1 for error)
        """
        if not self.initialize():
            return 1
        
        try:
            self.is_running = True
            
            # Log eclipse information
            timings = self.config.eclipse_timings
            self.logger.info("Eclipse timing:")
            self.logger.info(f"  C1 (First contact): {timings.c1}")
            self.logger.info(f"  C2 (Second contact): {timings.c2}")
            self.logger.info(f"  Max (Greatest eclipse): {timings.max}")
            self.logger.info(f"  C3 (Third contact): {timings.c3}")
            self.logger.info(f"  C4 (Fourth contact): {timings.c4}")
            
            # Validate eclipse timing sequence
            if not self.time_calculator.validate_eclipse_sequence():
                self.logger.error("Eclipse timing validation failed")
                return 1
            
            # Show camera information
            camera_info = self.camera_manager.get_camera_info()
            self.logger.info("Camera information:")
            for camera_id, info in camera_info.items():
                status = "ACTIVE" if info['active'] else "INACTIVE"
                self.logger.info(f"  Camera {camera_id}: {info['name']} ({status})")
            
            # Execute action sequence
            self.logger.info(f"Starting eclipse sequence: {len(self.config.actions)} actions")
            
            for i, action_config in enumerate(self.config.actions):
                if self.shutdown_requested:
                    self.logger.info("Shutdown requested, stopping sequence")
                    break
                
                self.logger.info(f"=== Action {i + 1}/{len(self.config.actions)} ===")
                
                success = self.scheduler.execute_action(action_config)
                
                if not success:
                    self.logger.error(f"Action {i + 1} failed")
                    # Continue with remaining actions unless in strict mode
                    if not self.options.get('strict_mode', False):
                        continue
                    else:
                        self.logger.error("Strict mode enabled, stopping sequence")
                        return 1
            
            # Show execution statistics
            stats = self.scheduler.get_execution_stats()
            self.logger.info("Execution complete:")
            self.logger.info(f"  Actions executed: {stats['actions_executed']}")
            self.logger.info(f"  Photos taken: {stats['photos_taken']}")
            self.logger.info(f"  Errors: {stats['execution_errors']}")
            
            if stats['execution_errors'] == 0:
                self.logger.info(SUCCESS_MESSAGES['sequence_complete'])
                return 0
            else:
                self.logger.warning("Sequence completed with errors")
                return 1
                
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
            return 1
        except Exception as e:
            self.logger.error(f"Runtime error: {e}", exc_info=True)
            return 1
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        self.is_running = False
        
        if self.camera_manager:
            try:
                self.logger.info("Disconnecting cameras...")
                self.camera_manager.disconnect_all()
            except Exception as e:
                self.logger.error(f"Error during camera cleanup: {e}")
        
        if self.logger:
            self.logger.info("Cleanup complete")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.shutdown_requested = True
        if self.logger:
            self.logger.info(f"Received signal {signum}, initiating shutdown...")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} - {APP_DESCRIPTION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s config_eclipse.txt
  %(prog)s config_eclipse.txt --test-mode
  %(prog)s config_eclipse.txt --cameras 0 1 2 --log-level DEBUG
  %(prog)s config_eclipse.txt --log-file /var/log/eclipse.log
        """
    )
    
    # Required arguments
    parser.add_argument(
        'config_file',
        help='Eclipse configuration file (e.g., SOLARECL.TXT)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Enable test mode (simulate captures without taking photos)'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        help='Log file path (default: eclipse_oz.log)'
    )
    
    parser.add_argument(
        '--cameras',
        nargs='+',
        type=int,
        help='Specific camera IDs to use (e.g., --cameras 0 1 2)'
    )
    
    parser.add_argument(
        '--strict-mode',
        action='store_true',
        help='Stop sequence on first action failure'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'{APP_NAME} {APP_VERSION}'
    )
    
    return parser


def main() -> int:
    """Main entry point."""
    # Parse command line arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Validate config file exists
    config_path = Path(args.config_file)
    if not config_path.exists():
        print(f"Error: Configuration file not found: {args.config_file}")
        return 1
    
    # Create controller with options
    options = {
        'test_mode': args.test_mode,
        'log_level': args.log_level,
        'log_file': args.log_file,
        'strict_mode': args.strict_mode
    }
    
    if args.cameras:
        options['cameras'] = args.cameras
    
    controller = EclipsePhotographyController(str(config_path), **options)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, controller.signal_handler)
    signal.signal(signal.SIGTERM, controller.signal_handler)
    
    # Run the application
    return controller.run()


if __name__ == "__main__":
    sys.exit(main())