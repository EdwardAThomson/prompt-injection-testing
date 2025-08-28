"""Configuration management for PromptExpand."""

import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, Optional


DEFAULT_CONFIG = {
    'input': {
        'path': 'prompts.txt',
        'format': 'auto'
    },
    'output': {
        'dir': './out',
        'write_csv': True,
        'write_jsonl': True
    },
    'models': {
        'safety': 'gpt-4o',
        'expand': 'gpt-4o'
    },
    'llm': {
        'temperature': 0.0,
        'max_tokens': 256,
        'max_tokens_expand': 800,
        'retry': {
            'attempts': 3,
            'backoff_sec': 2
        }
    },
    'run': {
        'stop_on_parse_error': False,
        'redact_in_report': False,
        'test_mode': False,
        'minimal_expansion': False,
        'feedback_mode': False,
        'no_expansion': False,
        'debug': False
    }
}


class Config:
    """Configuration manager that loads YAML and merges with CLI args."""
    
    def __init__(self, config_path: Optional[str] = None, cli_args: Optional[Dict] = None):
        self.config = DEFAULT_CONFIG.copy()
        
        # Load from YAML file if provided
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                self._merge_config(self.config, yaml_config)
        
        # Override with CLI args if provided
        if cli_args:
            self._apply_cli_overrides(cli_args)
    
    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge configuration dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _apply_cli_overrides(self, cli_args: Dict):
        """Apply CLI argument overrides to configuration."""
        # Map CLI args to config paths
        cli_mapping = {
            'input': ('input', 'path'),
            'format': ('input', 'format'),
            'out': ('output', 'dir'),
            'safety_model': ('models', 'safety'),
            'expand_model': ('models', 'expand'),
            'temperature': ('llm', 'temperature'),
            'max_tokens': ('llm', 'max_tokens'),
            'max_tokens_expand': ('llm', 'max_tokens_expand'),
            'csv': ('output', 'write_csv'),
            'jsonl': ('output', 'write_jsonl'),
            'redact': ('run', 'redact_in_report'),
            'stop_on_parse_error': ('run', 'stop_on_parse_error'),
            'test_mode': ('run', 'test_mode'),
            'minimal_expansion': ('run', 'minimal_expansion'),
            'feedback_mode': ('run', 'feedback_mode'),
            'no_expansion': ('run', 'no_expansion'),
            'debug': ('run', 'debug')
        }
        
        for cli_key, config_path in cli_mapping.items():
            if cli_key in cli_args and cli_args[cli_key] is not None:
                # Navigate to the nested config location
                current = self.config
                for key in config_path[:-1]:
                    current = current[key]
                current[config_path[-1]] = cli_args[cli_key]
    
    def get(self, *path):
        """Get configuration value by path (e.g., get('models', 'safety'))."""
        current = self.config
        for key in path:
            current = current[key]
        return current
    
    def __getitem__(self, key):
        return self.config[key]


def create_cli_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Prompt Safety & Expansion Evaluator',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Input/Output
    parser.add_argument('--input', help='Input file path (prompts.txt or prompts.jsonl)')
    parser.add_argument('--format', choices=['txt', 'jsonl', 'auto'], help='Input format')
    parser.add_argument('--out', help='Output directory')
    parser.add_argument('--config', help='Configuration YAML file path')
    
    # Models
    parser.add_argument('--safety-model', help='Model for safety classification')
    parser.add_argument('--expand-model', help='Model for prompt expansion')
    
    # LLM Parameters
    parser.add_argument('--temperature', type=float, help='LLM temperature')
    parser.add_argument('--max-tokens', type=int, help='Max tokens for safety classification')
    parser.add_argument('--max-tokens-expand', type=int, help='Max tokens for expansion')
    
    # Output formats
    parser.add_argument('--csv', action='store_true', help='Generate CSV output')
    parser.add_argument('--no-csv', action='store_false', dest='csv', help='Skip CSV output')
    parser.add_argument('--jsonl', action='store_true', help='Generate JSONL output')
    parser.add_argument('--no-jsonl', action='store_false', dest='jsonl', help='Skip JSONL output')
    
    # Runtime options
    parser.add_argument('--redact', action='store_true', help='Redact prompt text in reports')
    parser.add_argument('--debug', action='store_true', help='Save raw LLM exchanges')
    parser.add_argument('--test-mode', action='store_true', help='Process only first 5 prompts for testing')
    parser.add_argument('--minimal-expansion', action='store_true', help='Use minimal expansion mode (less verbose)')
    parser.add_argument('--feedback-mode', action='store_true', help='Use feedback mode with suspicious system prompt and written explanations')
    parser.add_argument('--no-expansion', action='store_true', help='Skip expansion step - only classify original prompts')
    parser.add_argument('--stop-on-parse-error', action='store_true', 
                       help='Stop processing on JSON parse errors')
    
    return parser


def load_config(config_path: Optional[str] = None, cli_args: Optional[Dict] = None) -> Config:
    """Load configuration from YAML file and CLI arguments."""
    return Config(config_path, cli_args)
