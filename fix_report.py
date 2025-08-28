#!/usr/bin/env python3
"""
Script to regenerate reports from existing JSON debug files.
Useful when report generation logic has been fixed but you don't want to re-run LLM calls.
"""

import json
import sys
from pathlib import Path
from typing import List
from report import ReportGenerator, PromptResult


def load_results_from_json_logs(log_dir: Path) -> List[PromptResult]:
    """Load PromptResult objects from JSON debug files."""
    results = []
    
    # Find all JSON files in logs directory
    json_files = sorted(log_dir.glob("p-*.json"))
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse expanded_judgement from raw_responses if available
        expanded_judgement = data['original_judgement']  # fallback
        if 'raw_responses' in data and 'expanded_judgement' in data['raw_responses']:
            try:
                expanded_judgement = json.loads(data['raw_responses']['expanded_judgement'])
            except json.JSONDecodeError:
                expanded_judgement = data['original_judgement']
        
        # Convert back to PromptResult object
        result = PromptResult(
            id=data['id'],
            original_prompt=data['original_prompt'],
            original_judgement=data['original_judgement'],
            expanded_prompt=data.get('expanded_prompt', data['original_prompt']),  # fallback for no-expansion
            expanded_judgement=expanded_judgement,
            model_safety=data['meta']['model_safety'],
            model_expand=data['meta']['model_expand'],
            latency_ms=data['meta']['latency_ms'],
            no_expansion=data['meta'].get('no_expansion', False)
        )
        
        results.append(result)
    
    return results


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python fix_report.py <output_directory>")
        print("Example: python fix_report.py test_out_gpt-4o_gpt-4o_20250826_225752")
        sys.exit(1)
    
    output_dir = Path(sys.argv[1])
    log_dir = output_dir / 'logs'
    
    if not log_dir.exists():
        print(f"Error: Logs directory not found: {log_dir}")
        sys.exit(1)
    
    print(f"Loading results from {log_dir}...")
    results = load_results_from_json_logs(log_dir)
    
    if not results:
        print("No JSON files found in logs directory")
        sys.exit(1)
    
    print(f"Loaded {len(results)} results")
    
    # Extract execution info from first JSON file for report header
    execution_info = None
    json_files = sorted(log_dir.glob("p-*.json"))
    if json_files:
        with open(json_files[0], 'r', encoding='utf-8') as f:
            first_data = json.load(f)
            execution_info = first_data.get('execution_info')
    
    # Regenerate reports with fixed logic
    print("Regenerating reports...")
    report_generator = ReportGenerator(output_dir=str(output_dir), redact=False)
    
    # Pass execution info to report generator
    if execution_info:
        report_generator._execution_info = execution_info
    
    report_generator.generate_reports(results, write_csv=True, write_jsonl=True)
    
    print(f"Reports regenerated in {output_dir}")
    print("- report.md (fixed)")
    print("- results.csv (fixed)")
    print("- results.jsonl (fixed)")


if __name__ == '__main__':
    main()
