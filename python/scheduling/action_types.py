"""
Action type definitions for Eclipse Photography Controller.

Defines the different types of photographic actions that can be scheduled.
"""

from enum import Enum
from abc import ABC, abstractmethod
from ..config.eclipse_config import ActionConfig



class ActionType(Enum):
    """Enumeration of supported action types."""
    PHOTO = "Photo"
    LOOP = "Boucle"
    INTERVAL = "Interval"


class BaseAction(ABC):
    """Base class for all photographic actions."""
    
    def __init__(self, config: ActionConfig):
        self.config = config
        self.action_type = ActionType(config.action_type)
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate action configuration."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of the action."""
        pass


class PhotoAction(BaseAction):
    """Single photo action at a specific time."""
    
    def validate(self) -> bool:
        """Validate photo action configuration."""
        if self.config.action_type != ActionType.PHOTO.value:
            return False
        
        # Photo actions don't need end_time or interval
        return (self.config.start_time is not None and 
                self.config.time_ref is not None and 
                self.config.start_operator is not None)
    
    def get_description(self) -> str:
        """Get description of photo action."""
        if self.config.time_ref == '-':
            time_desc = f"at {self.config.start_time}"
        else:
            time_desc = f"at {self.config.time_ref} {self.config.start_operator} {self.config.start_time}"
        
        settings_desc = []
        if self.config.iso:
            settings_desc.append(f"ISO {self.config.iso}")
        if self.config.aperture:
            settings_desc.append(f"f/{self.config.aperture}")
        if self.config.shutter_speed:
            settings_desc.append(f"{self.config.shutter_speed}s")
        
        settings = " ".join(settings_desc) if settings_desc else "default settings"
        
        return f"Photo {time_desc} with {settings}"


class LoopAction(BaseAction):
    """Loop action with regular intervals between start and end times."""
    
    def validate(self) -> bool:
        """Validate loop action configuration."""
        if self.config.action_type != ActionType.LOOP.value:
            return False
        
        return (self.config.start_time is not None and 
                self.config.end_time is not None and 
                self.config.interval_or_count is not None and
                self.config.interval_or_count > 0)
    
    def get_description(self) -> str:
        """Get description of loop action."""
        start_desc = self._format_time_reference('start')
        end_desc = self._format_time_reference('end')
        
        settings_desc = []
        if self.config.iso:
            settings_desc.append(f"ISO {self.config.iso}")
        if self.config.aperture:
            settings_desc.append(f"f/{self.config.aperture}")
        if self.config.shutter_speed:
            settings_desc.append(f"{self.config.shutter_speed}s")
        
        settings = " ".join(settings_desc) if settings_desc else "default settings"
        
        return (f"Loop from {start_desc} to {end_desc} "
                f"every {self.config.interval_or_count}s with {settings}")
    
    def _format_time_reference(self, ref_type: str) -> str:
        """Format time reference for display."""
        if ref_type == 'start':
            if self.config.time_ref == '-':
                return str(self.config.start_time)
            else:
                return f"{self.config.time_ref} {self.config.start_operator} {self.config.start_time}"
        else:  # end
            return f"{self.config.time_ref} {self.config.end_operator} {self.config.end_time}"


class IntervalAction(BaseAction):
    """Interval action with a specified number of photos over a time period."""
    
    def validate(self) -> bool:
        """Validate interval action configuration."""
        if self.config.action_type != ActionType.INTERVAL.value:
            return False
        
        return (self.config.start_time is not None and 
                self.config.end_time is not None and 
                self.config.interval_or_count is not None and
                self.config.interval_or_count > 0)
    
    def get_description(self) -> str:
        """Get description of interval action."""
        start_desc = self._format_time_reference('start')
        end_desc = self._format_time_reference('end')
        
        settings_desc = []
        if self.config.iso:
            settings_desc.append(f"ISO {self.config.iso}")
        if self.config.aperture:
            settings_desc.append(f"f/{self.config.aperture}")
        if self.config.shutter_speed:
            settings_desc.append(f"{self.config.shutter_speed}s")
        
        settings = " ".join(settings_desc) if settings_desc else "default settings"
        
        return (f"Interval: {int(self.config.interval_or_count)} photos "
                f"from {start_desc} to {end_desc} with {settings}")
    
    def _format_time_reference(self, ref_type: str) -> str:
        """Format time reference for display."""
        if ref_type == 'start':
            if self.config.time_ref == '-':
                return str(self.config.start_time)
            else:
                return f"{self.config.time_ref} {self.config.start_operator} {self.config.start_time}"
        else:  # end
            return f"{self.config.time_ref} {self.config.end_operator} {self.config.end_time}"


def create_action(config: ActionConfig) -> BaseAction:
    """
    Factory function to create appropriate action object.
    
    Args:
        config: Action configuration
        
    Returns:
        Appropriate action object
        
    Raises:
        ValueError: If action type is unknown
    """
    action_map = {
        ActionType.PHOTO.value: PhotoAction,
        ActionType.LOOP.value: LoopAction,
        ActionType.INTERVAL.value: IntervalAction
    }
    
    action_class = action_map.get(config.action_type)
    if not action_class:
        raise ValueError(f"Unknown action type: {config.action_type}")
    
    action = action_class(config)
    
    if not action.validate():
        raise ValueError(f"Invalid configuration for {config.action_type} action")
    
    return action