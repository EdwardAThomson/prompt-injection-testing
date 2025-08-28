"""Prompt loader for reading from txt and jsonl files."""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple


class PromptData:
    """Container for a single prompt with metadata."""
    
    def __init__(self, id: str, text: str, source_line: int = None):
        self.id = id
        self.text = text
        self.source_line = source_line
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'text': self.text,
            'source_line': self.source_line
        }


def detect_format(file_path: str) -> str:
    """Auto-detect file format based on extension and content."""
    path = Path(file_path)
    
    if path.suffix.lower() == '.jsonl':
        return 'jsonl'
    elif path.suffix.lower() == '.txt':
        return 'txt'
    
    # Try to detect by content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('{') and first_line.endswith('}'):
                # Try to parse as JSON
                json.loads(first_line)
                return 'jsonl'
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    
    # Default to txt
    return 'txt'


def load_txt_prompts(file_path: str) -> List[PromptData]:
    """Load prompts from a text file (one per line)."""
    prompts = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:  # Skip empty lines
                prompt_id = f"p-{line_num:04d}"
                prompts.append(PromptData(prompt_id, line, line_num))
    
    return prompts


def load_jsonl_prompts(file_path: str) -> List[PromptData]:
    """Load prompts from a JSONL file."""
    prompts = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                
                # Extract id and text
                if 'id' in data and 'text' in data:
                    prompt_id = data['id']
                    text = data['text']
                elif 'text' in data:
                    prompt_id = f"p-{line_num:04d}"
                    text = data['text']
                else:
                    raise ValueError(f"Missing 'text' field in line {line_num}")
                
                prompts.append(PromptData(prompt_id, text, line_num))
                
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_num}: {e}")
    
    return prompts


def load_prompts(file_path: str, format: str = 'auto') -> Tuple[List[PromptData], str]:
    """
    Load prompts from file.
    
    Args:
        file_path: Path to the prompts file
        format: Format ('txt', 'jsonl', or 'auto')
    
    Returns:
        Tuple of (prompts_list, detected_format)
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Prompts file not found: {file_path}")
    
    # Auto-detect format if needed
    if format == 'auto':
        format = detect_format(file_path)
    
    # Load based on format
    if format == 'txt':
        prompts = load_txt_prompts(file_path)
    elif format == 'jsonl':
        prompts = load_jsonl_prompts(file_path)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    if not prompts:
        raise ValueError(f"No prompts found in {file_path}")
    
    return prompts, format
