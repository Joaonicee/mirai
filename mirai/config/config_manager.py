"""
Configuration Manager for MirAi
Handles loading, saving, and managing application settings.
"""

import json
import os
from typing import Any, Dict, Optional
from pathlib import Path


class ConfigManager:
    """Manages application configuration with persistence."""
    
    DEFAULT_CONFIG = {
        "fov_radius": 150,
        "aim_smoothness": 0.5,
        "confidence_threshold": 0.5,
        "target_classes": [],
        "hotkey_toggle": "insert",
        "show_overlay": True,
        "show_fov_circle": True,
        "aim_part": "center",
        "head_offset": 0.2,
        "target_fps": 60,
        "model_path": "",
        "aim_speed": 1.0,
        "max_detections": 10,
        "triggerbot_enabled": False,
        "triggerbot_mode": "hold",  # rapid, hold, single
        "triggerbot_delay": 0.1,    # delay before shooting
        "triggerbot_interval": 0.1,  # interval between shots (rapid)
        "triggerbot_magnet": True   # should trigger only if already aiming at target
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the config manager.
        
        Args:
            config_path: Path to the config file. If None, uses default location.
        """
        if config_path is None:
            # Use user's appdata for persistence
            app_data = os.getenv('APPDATA', os.path.expanduser('~'))
            self.config_dir = Path(app_data) / 'MirAi'
            self.config_path = self.config_dir / 'config.json'
        else:
            self.config_path = Path(config_path)
            self.config_dir = self.config_path.parent
            
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file or create with defaults."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to handle missing keys
                self._config = {**self.DEFAULT_CONFIG, **loaded_config}
            else:
                self._config = self.DEFAULT_CONFIG.copy()
                self._save_config()
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Config] Error loading config: {e}. Using defaults.")
            self._config = self.DEFAULT_CONFIG.copy()
    
    def _save_config(self) -> None:
        """Save current configuration to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4)
        except IOError as e:
            print(f"[Config] Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key
            default: Default value if key doesn't exist
            
        Returns:
            The configuration value
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key
            value: The value to set
            save: Whether to save to file immediately
        """
        self._config[key] = value
        if save:
            self._save_config()
    
    def update(self, updates: Dict[str, Any], save: bool = True) -> None:
        """
        Update multiple configuration values.
        
        Args:
            updates: Dictionary of key-value pairs to update
            save: Whether to save to file immediately
        """
        self._config.update(updates)
        if save:
            self._save_config()
    
    def reset_to_defaults(self) -> None:
        """Reset all configuration to default values."""
        self._config = self.DEFAULT_CONFIG.copy()
        self._save_config()
    
    @property
    def fov_radius(self) -> int:
        return self._config.get('fov_radius', 150)
    
    @fov_radius.setter
    def fov_radius(self, value: int) -> None:
        self.set('fov_radius', max(10, min(500, value)))
    
    @property
    def aim_smoothness(self) -> float:
        return self._config.get('aim_smoothness', 0.5)
    
    @aim_smoothness.setter
    def aim_smoothness(self, value: float) -> None:
        self.set('aim_smoothness', max(0.1, min(1.0, value)))
    
    @property
    def confidence_threshold(self) -> float:
        return self._config.get('confidence_threshold', 0.5)
    
    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        self.set('confidence_threshold', max(0.1, min(1.0, value)))
    
    @property
    def target_classes(self) -> list:
        return self._config.get('target_classes', [])
    
    @target_classes.setter
    def target_classes(self, value: list) -> None:
        self.set('target_classes', value)
    
    @property
    def show_overlay(self) -> bool:
        return self._config.get('show_overlay', True)
    
    @show_overlay.setter
    def show_overlay(self, value: bool) -> None:
        self.set('show_overlay', value)
    
    @property
    def show_fov_circle(self) -> bool:
        return self._config.get('show_fov_circle', True)
    
    @show_fov_circle.setter
    def show_fov_circle(self, value: bool) -> None:
        self.set('show_fov_circle', value)
    
    @property
    def head_offset(self) -> float:
        """Head offset as percentage of bounding box height (0.0 - 1.0)."""
        return self._config.get('head_offset', 0.2)
    
    @head_offset.setter
    def head_offset(self, value: float) -> None:
        self.set('head_offset', max(0.0, min(1.0, value)))
    
    @property
    def target_fps(self) -> int:
        """Target FPS for the detection loop."""
        return self._config.get('target_fps', 60)
    
    @target_fps.setter
    def target_fps(self, value: int) -> None:
        self.set('target_fps', max(1, min(240, value)))
    
    @property
    def model_path(self) -> str:
        return self._config.get('model_path', '')
    
    @model_path.setter
    def model_path(self, value: str) -> None:
        self.set('model_path', value)
    
    @property
    def aim_speed(self) -> float:
        return self._config.get('aim_speed', 1.0)
    
    @aim_speed.setter
    def aim_speed(self, value: float) -> None:
        self.set('aim_speed', max(0.1, min(5.0, value)))

    @property
    def triggerbot_enabled(self) -> bool:
        return self._config.get('triggerbot_enabled', False)

    @triggerbot_enabled.setter
    def triggerbot_enabled(self, value: bool) -> None:
        self.set('triggerbot_enabled', value)

    @property
    def triggerbot_mode(self) -> str:
        return self._config.get('triggerbot_mode', 'hold')

    @triggerbot_mode.setter
    def triggerbot_mode(self, value: str) -> None:
        if value in ['rapid', 'hold', 'single']:
            self.set('triggerbot_mode', value)

    @property
    def triggerbot_delay(self) -> float:
        return self._config.get('triggerbot_delay', 0.1)

    @triggerbot_delay.setter
    def triggerbot_delay(self, value: float) -> None:
        self.set('triggerbot_delay', max(0.0, min(2.0, value)))

    @property
    def triggerbot_interval(self) -> float:
        return self._config.get('triggerbot_interval', 0.1)

    @triggerbot_interval.setter
    def triggerbot_interval(self, value: float) -> None:
        self.set('triggerbot_interval', max(0.01, min(1.0, value)))
        
    @property
    def triggerbot_magnet(self) -> bool:
        return self._config.get('triggerbot_magnet', True)

    @triggerbot_magnet.setter
    def triggerbot_magnet(self, value: bool) -> None:
        self.set('triggerbot_magnet', value)

    @property
    def hotkey_triggerbot(self) -> str:
        return self._config.get('hotkey_triggerbot', 'end')
        
    @hotkey_triggerbot.setter
    def hotkey_triggerbot(self, value: str) -> None:
        self.set('hotkey_triggerbot', value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return a copy of the current configuration."""
        return self._config.copy()


# Global config instance
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance
