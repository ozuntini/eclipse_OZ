"""
Logging configuration for Eclipse Photography Controller.

Provides centralized logging setup with color support and file output.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False

from .constants import LOG_FORMAT, LOG_DATE_FORMAT


def setup_logging(level: str = "INFO", 
                  log_file: Optional[str] = None,
                  enable_color: bool = True) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logging output
        enable_color: Enable colored console output if available
        
    Returns:
        Root logger instance
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Configure console formatter
    if enable_color and COLORLOG_AVAILABLE:
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt=LOG_DATE_FORMAT,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    else:
        console_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if requested
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        
        file_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Log initial setup message
    logger.info(f"Logging initialized at {level} level")
    if log_file:
        logger.info(f"Log file: {log_file}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class EclipseLoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter for eclipse-specific context.
    
    Adds eclipse phase and camera information to log messages.
    """
    
    def __init__(self, logger: logging.Logger, extra: dict):
        super().__init__(logger, extra)
    
    def process(self, msg, kwargs):
        """Add context information to log messages."""
        extra_info = []
        
        if 'phase' in self.extra:
            extra_info.append(f"Phase:{self.extra['phase']}")
        
        if 'camera_id' in self.extra:
            extra_info.append(f"Cam:{self.extra['camera_id']}")
        
        if 'action_type' in self.extra:
            extra_info.append(f"Action:{self.extra['action_type']}")
        
        if extra_info:
            msg = f"[{' '.join(extra_info)}] {msg}"
        
        return msg, kwargs


def create_phase_logger(phase: str, base_logger: Optional[logging.Logger] = None) -> EclipseLoggerAdapter:
    """
    Create a logger for a specific eclipse phase.
    
    Args:
        phase: Eclipse phase name (e.g., "C1", "C2", "Max", "C3", "C4")
        base_logger: Base logger to wrap, or None for root logger
        
    Returns:
        Logger adapter with phase context
    """
    if base_logger is None:
        base_logger = logging.getLogger()
    
    return EclipseLoggerAdapter(base_logger, {'phase': phase})


def create_camera_logger(camera_id: int, base_logger: Optional[logging.Logger] = None) -> EclipseLoggerAdapter:
    """
    Create a logger for a specific camera.
    
    Args:
        camera_id: Camera identifier
        base_logger: Base logger to wrap, or None for root logger
        
    Returns:
        Logger adapter with camera context
    """
    if base_logger is None:
        base_logger = logging.getLogger()
    
    return EclipseLoggerAdapter(base_logger, {'camera_id': camera_id})


def create_action_logger(action_type: str, base_logger: Optional[logging.Logger] = None) -> EclipseLoggerAdapter:
    """
    Create a logger for a specific action type.
    
    Args:
        action_type: Action type (Photo, Boucle, Interval)
        base_logger: Base logger to wrap, or None for root logger
        
    Returns:
        Logger adapter with action context
    """
    if base_logger is None:
        base_logger = logging.getLogger()
    
    return EclipseLoggerAdapter(base_logger, {'action_type': action_type})


# Convenience function for quick setup
def quick_setup(level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Quick logging setup with default Eclipse_OZ configuration.
    
    Args:
        level: Logging level
        log_to_file: Whether to also log to file
        
    Returns:
        Configured logger
    """
    log_file = "eclipse_oz.log" if log_to_file else None
    return setup_logging(level, log_file)