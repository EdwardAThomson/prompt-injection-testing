"""Configuration management for PromptExpand."""

import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, Optional


# ── Default models (single source of truth) ──────────────────────────
# Change these when upgrading to newer models. Everything else reads from here.
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_WEAK_MODEL = "gpt-5.4-mini"


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
        'safety': DEFAULT_MODEL,
        'expand': DEFAULT_MODEL
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
    },
    'detectors': {
        'enabled': ['llm_judge'],
        'llm_judge': {},
        'regex': {
            'risk_threshold': 0.5,
        },
        'bert': {
            'model': 'protectai/deberta-v3-base-prompt-injection-v2',
            'mode': 'classification',
            'threshold': 0.5,
            'device': 'cpu',
        },
        'weak_model': {
            'model': DEFAULT_WEAK_MODEL,
            'temperature': 0.0,
        },
        'scramblegate': {
            'scramble_mode': 'probabilistic',
            'risk_threshold': 0.75,
            'window_tokens': 800,
            'stride_tokens': 400,
            'views_per_window': 5,
            'use_llm_probe': True,
        },
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
        
        # Boolean store_true flags: only override config when True
        # (False just means the flag wasn't passed, not an explicit choice)
        bool_flags = {
            'redact', 'stop_on_parse_error', 'test_mode',
            'minimal_expansion', 'feedback_mode', 'no_expansion', 'debug',
        }
        # csv/jsonl use store_true (--csv) and store_false (--no-csv).
        # Argparse defaults csv/jsonl to None when neither flag is passed.
        # --csv sets True, --no-csv sets False. We handle them below.

        for cli_key, config_path in cli_mapping.items():
            value = cli_args.get(cli_key)
            if value is None:
                continue
            if cli_key in bool_flags and value is False:
                continue
            current = self.config
            for key in config_path[:-1]:
                current = current[key]
            current[config_path[-1]] = value

        # Handle detector-specific overrides
        if cli_args.get('detectors'):
            self.config['detectors']['enabled'] = [
                d.strip() for d in cli_args['detectors'].split(',')
            ]
        if cli_args.get('scramble_mode'):
            self.config['detectors']['scramblegate']['scramble_mode'] = cli_args['scramble_mode']
        if cli_args.get('bert_model'):
            self.config['detectors']['bert']['model'] = cli_args['bert_model']
        if cli_args.get('weak_model'):
            self.config['detectors']['weak_model']['model'] = cli_args['weak_model']
        if cli_args.get('no_llm_probe'):
            self.config['detectors']['scramblegate']['use_llm_probe'] = False
    
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
    parser.add_argument('--csv', action='store_true', default=None, help='Generate CSV output')
    parser.add_argument('--no-csv', action='store_false', dest='csv', help='Skip CSV output')
    parser.add_argument('--jsonl', action='store_true', default=None, help='Generate JSONL output')
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

    # Detector options
    parser.add_argument('--detectors', type=str,
                       help='Comma-separated list of detectors to run (e.g. llm_judge,regex,bert)')
    parser.add_argument('--scramble-mode', type=str,
                       help='ScrambleGate scramble mode (e.g. probabilistic, broken_probabilistic)')
    parser.add_argument('--bert-model', type=str,
                       help='BERT model name for bert detector')
    parser.add_argument('--weak-model', type=str,
                       help='Model name for weak model detector (e.g. gpt-5.4-mini)')
    parser.add_argument('--no-llm-probe', action='store_true',
                       help='Disable ScrambleGate LLM probe (rules-only mode)')

    return parser


def load_config(config_path: Optional[str] = None, cli_args: Optional[Dict] = None) -> Config:
    """Load configuration from YAML file and CLI arguments."""
    return Config(config_path, cli_args)
