"""Configuration management for digdag graph."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml

from .exceptions import ConfigurationError


class Config:
    """Configuration manager supporting CLI args, env vars, and config files."""
    
    # Default configuration
    DEFAULTS = {
        'output_dir': 'graphs',
        'graph_format': 'svg',
        'graph_direction': 'LR',
        'include_schedule': True,
        'verbose': False,
        'quiet': False,
        'max_depth': None,
        'exclude_patterns': [],
        'include_patterns': [],
        'template_dir': None,
        'layer_patterns': [
            {'name': 'source', 'label': 'Source Tables', 'color': '#FFE6CC', 'patterns': ['src_']},
            {'name': 'staging', 'label': 'Staging Tables', 'color': '#DAE8FC', 'patterns': ['_stg', 'staging']},
            {'name': 'golden', 'label': 'Golden Tables', 'color': '#D5E8D4', 'patterns': ['rr_gldn', 'gldn', 'golden']},
        ],
    }
    
    # Environment variable mappings
    ENV_MAPPINGS = {
        'output_dir': ['OUTPUT_DIR', 'GRAPH_OUTPUT_DIR'],
        'graph_format': ['GRAPH_FORMAT'],
        'graph_direction': ['GRAPH_DIRECTION'],
        'include_schedule': ['INCLUDE_SCHEDULE'],
        'exclude_patterns': ['EXCLUDE_PATTERNS'],
        'include_patterns': ['INCLUDE_PATTERNS'],
        'template_dir': ['TEMPLATE_DIR'],
        'max_depth': ['MAX_GRAPH_DEPTH'],
    }
    
    def __init__(self, config_file: Optional[Path] = None, cli_args: Optional[Dict[str, Any]] = None):
        """Initialize configuration.
        
        Priority: CLI args > Environment vars > Config file > Defaults
        
        Args:
            config_file: Path to YAML configuration file
            cli_args: Dictionary of CLI arguments
        """
        self.config = self.DEFAULTS.copy()
        
        # Load from config file
        if config_file:
            self._load_config_file(config_file)
        
        # Load from environment variables
        self._load_from_env()
        
        # Override with CLI arguments
        if cli_args:
            self._load_from_cli(cli_args)
    
    def _load_config_file(self, config_file: Path):
        """Load configuration from YAML file."""
        if not config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {config_file}")
        
        try:
            with config_file.open('r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f) or {}
            
            # Flatten nested structure if needed
            if 'output' in file_config:
                self.config['output_dir'] = file_config['output'].get('directory', self.config['output_dir'])
                self.config['graph_format'] = file_config['output'].get('format', self.config['graph_format'])

            if 'graph' in file_config:
                graph_config = file_config['graph']
                self.config['graph_direction'] = graph_config.get('direction', self.config['graph_direction'])
                self.config['max_depth'] = graph_config.get('max_depth', self.config['max_depth'])
                self.config['include_schedule'] = graph_config.get('include_schedule', self.config['include_schedule'])
            
            if 'filters' in file_config:
                self.config['exclude_patterns'] = file_config['filters'].get('exclude_patterns', self.config['exclude_patterns'])
                self.config['include_patterns'] = file_config['filters'].get('include_only', self.config['include_patterns'])
            
            if 'lineage' in file_config and 'layers' in file_config['lineage']:
                self.config['layer_patterns'] = file_config['lineage']['layers']
            
            if 'output_pages' in file_config:
                template_dir = file_config['output_pages'].get('template_dir')
                if template_dir:
                    self.config['template_dir'] = template_dir
                    
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing configuration file: {e}")
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        for key, env_vars in self.ENV_MAPPINGS.items():
            for env_var in env_vars:
                value = os.getenv(env_var)
                if value is not None:
                    # Parse value based on type
                    if key in ['exclude_patterns', 'include_patterns']:
                        # Comma-separated list
                        self.config[key] = [p.strip() for p in value.split(',') if p.strip()]
                    elif key == 'include_schedule':
                        # Boolean
                        self.config[key] = value.lower() in ('true', '1', 'yes')
                    elif key == 'max_depth':
                        # Integer
                        try:
                            self.config[key] = int(value)
                        except ValueError:
                            pass
                    else:
                        self.config[key] = value
                    break  # Use first matching env var
    
    def _load_from_cli(self, cli_args: Dict[str, Any]):
        """Load configuration from CLI arguments."""
        for key, value in cli_args.items():
            if value is not None:
                self.config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dict syntax."""
        return self.config[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self.config
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self.config.copy()
