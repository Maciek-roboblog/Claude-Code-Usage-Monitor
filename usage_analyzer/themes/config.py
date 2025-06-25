"""Configuration management for theme system."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from .themes import ThemeType


class ThemeConfig:
    """Manages theme configuration and user preferences."""
    
    def __init__(self):
        self.config_dir = Path.home() / '.claude-monitor'
        self.config_file = self.config_dir / 'config.yaml'
        self._config_cache: Optional[Dict[str, Any]] = None
    
    def get_user_theme_preference(self) -> Optional[ThemeType]:
        """Get user's theme preference from config file.
        
        Returns:
            ThemeType if set, None if not configured
        """
        config = self._load_config()
        theme_str = config.get('theme')
        
        if theme_str:
            try:
                return ThemeType(theme_str.lower())
            except ValueError:
                pass
                
        return None
    
    def set_user_theme_preference(self, theme: ThemeType) -> None:
        """Set user's theme preference in config file.
        
        Args:
            theme: Theme to set as preference
        """
        config = self._load_config()
        config['theme'] = theme.value
        self._save_config(config)
        self._config_cache = None  # Clear cache
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        if self._config_cache is not None:
            return self._config_cache
            
        config = {}
        
        if self.config_file.exists():
            try:
                import yaml
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
            except (ImportError, Exception):
                # Fallback to simple key=value parsing if yaml not available
                try:
                    with open(self.config_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if '=' in line and not line.startswith('#'):
                                key, value = line.split('=', 1)
                                config[key.strip()] = value.strip()
                except Exception:
                    pass
        
        self._config_cache = config
        return config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration dictionary to save
        """
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
        try:
            import yaml
            with open(self.config_file, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
        except ImportError:
            # Fallback to simple key=value format
            with open(self.config_file, 'w') as f:
                f.write("# Claude Monitor Configuration\n")
                for key, value in config.items():
                    f.write(f"{key}={value}\n")
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about configuration.
        
        Returns:
            Debug information dictionary
        """
        return {
            'config_dir': str(self.config_dir),
            'config_file': str(self.config_file),
            'config_exists': self.config_file.exists(),
            'user_preference': self.get_user_theme_preference().value if self.get_user_theme_preference() else None,
            'config_content': self._load_config()
        }