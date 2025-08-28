#!/usr/bin/env python3
"""Main CLI interface for PromptExpand."""

import sys
from pathlib import Path
from typing import List
from datetime import datetime

from config import create_cli_parser, load_config
from loader import load_prompts, PromptData
from judge import SafetyJudge, SAFETY_USER_TEMPLATE, SAFETY_FEEDBACK_USER_TEMPLATE
from expand import PromptExpander
from report import ReportGenerator, PromptResult


def main():
    """Main CLI entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Store original command for logging
    original_command = ' '.join(sys.argv)
    
    try:
        # Load configuration
        config = load_config(args.config, vars(args))
        
        # Validate input file exists
        input_path = config.get('input', 'path')
        if not Path(input_path).exists():
            print(f"Error: Input file not found: {input_path}")
            sys.exit(1)
        
        # Create output directory with timestamp and model info
        base_output_dir = config.get('output', 'dir')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safety_model = config.get('models', 'safety').replace('/', '_')
        expand_model = config.get('models', 'expand').replace('/', '_')
        output_dir = f"{base_output_dir}_{safety_model}_{expand_model}_{timestamp}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Load prompts
        print(f"Loading prompts from {input_path}...")
        prompts, detected_format = load_prompts(
            input_path, 
            config.get('input', 'format')
        )
        # Apply test mode if enabled
        if config.get('run', 'test_mode'):
            prompts = prompts[:5]
            print(f"TEST MODE: Using first 5 prompts only")
        print(f"Loaded {len(prompts)} prompts ({detected_format} format)")
        
        # Initialize components
        # Create baseline judge (no feedback mode) for comparison
        baseline_judge = SafetyJudge(
            model=config.get('models', 'safety'),
            temperature=config.get('llm', 'temperature'),
            max_tokens=config.get('llm', 'max_tokens'),
            retry_attempts=config.get('llm', 'retry', 'attempts'),
            retry_backoff=config.get('llm', 'retry', 'backoff_sec'),
            stop_on_parse_error=config.get('run', 'stop_on_parse_error'),
            feedback_mode=False  # Always baseline
        )
        
        # Create actual safety judge with user settings
        safety_judge = SafetyJudge(
            model=config.get('models', 'safety'),
            temperature=config.get('llm', 'temperature'),
            max_tokens=config.get('llm', 'max_tokens'),
            retry_attempts=config.get('llm', 'retry', 'attempts'),
            retry_backoff=config.get('llm', 'retry', 'backoff_sec'),
            stop_on_parse_error=config.get('run', 'stop_on_parse_error'),
            feedback_mode=config.get('run', 'feedback_mode')
        )
        
        expander = PromptExpander(
            model=config.get('models', 'expand'),
            temperature=0.7,  # Use higher temperature for expansion
            max_tokens=config.get('llm', 'max_tokens_expand'),
            retry_attempts=config.get('llm', 'retry', 'attempts'),
            retry_backoff=config.get('llm', 'retry', 'backoff_sec'),
            minimal_mode=config.get('run', 'minimal_expansion')
        )
        
        report_generator = ReportGenerator(
            output_dir=output_dir,
            redact=config.get('run', 'redact_in_report')
        )
        
        # Process prompts
        print("\nProcessing prompts...")
        results = process_prompts(
            prompts, 
            safety_judge, 
            expander, 
            debug=config.get('run', 'debug'),
            output_dir=output_dir,
            config=config,
            baseline_judge=baseline_judge,
            original_command=original_command
        )
        print(f"\nGenerating reports in {output_dir}...")
        report_generator.generate_reports(
            results,
            write_csv=config.get('output', 'write_csv'),
            write_jsonl=config.get('output', 'write_jsonl')
        )
        
        print(f"Analysis complete! Check {output_dir}/report.md for results.")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)


def process_prompts(prompts: List[PromptData], safety_judge: SafetyJudge, 
                   expander: PromptExpander, debug: bool = False, 
                   output_dir: str = None, config = None, 
                   baseline_judge: SafetyJudge = None, original_command: str = None) -> List[PromptResult]:
    """Process all prompts through the safety and expansion pipeline."""
    results = []
    
    # Create debug directory if needed
    debug_dir = None
    if debug and output_dir:
        debug_dir = Path(output_dir) / 'logs'
        debug_dir.mkdir(exist_ok=True)
    
    for i, prompt_data in enumerate(prompts, 1):
        print(f"Processing {i}/{len(prompts)}: {prompt_data.id}")
        
        try:
            # Step 1: ALWAYS run baseline first (no feedback, no expansion)
            print(f"  → Baseline classification (no feedback)...")
            baseline_judge = SafetyJudge(
                model=safety_judge.model,
                temperature=safety_judge.temperature,
                max_tokens=safety_judge.max_tokens,
                retry_attempts=safety_judge.retry_attempts,
                retry_backoff=safety_judge.retry_backoff,
                stop_on_parse_error=safety_judge.stop_on_parse_error,
                feedback_mode=False  # Force baseline mode
            )
            original_judgement = baseline_judge.classify(prompt_data.text)
            
            # Step 2: Check if we should skip expansion
            if config and config.get('run', 'no_expansion'):
                # No expansion mode - use original prompt as "expanded" prompt
                expanded_text = prompt_data.text
                expand_latency = 0
                # Use the configured safety judge (may have feedback mode)
                expanded_judgement = safety_judge.classify(prompt_data.text)
                print(f"  → Modified classification (feedback={safety_judge.feedback_mode})...")
            else:
                # Step 3: Expand prompt
                print(f"  → Expanding prompt...")
                expanded_text, expand_latency = expander.expand(prompt_data.text)
                
                # Step 4: Judge expanded prompt with configured settings
                print(f"  → Modified classification (feedback={safety_judge.feedback_mode})...")
                expanded_judgement = safety_judge.classify(expanded_text)
            
            # Create result
            no_expansion_mode = config and config.get('run', 'no_expansion')
            result = PromptResult(
                id=prompt_data.id,
                original_prompt=prompt_data.text,
                original_judgement=original_judgement.to_dict(),
                expanded_prompt=expanded_text,
                expanded_judgement=expanded_judgement.to_dict(),
                model_safety=safety_judge.model,
                model_expand=expander.model,
                latency_ms={
                    'judge_original': original_judgement.latency_ms,
                    'expand': expand_latency,
                    'judge_expanded': expanded_judgement.latency_ms
                },
                no_expansion=no_expansion_mode
            )
            
            results.append(result)
            
            # Debug logging
            if debug_dir:
                debug_file = debug_dir / f"{prompt_data.id}.json"
                with open(debug_file, 'w') as f:
                    import json
                    debug_data = result.to_dict()
                    debug_data['raw_responses'] = {
                        'original_judgement': original_judgement.raw_response,
                        'expanded_judgement': expanded_judgement.raw_response
                    }
                    debug_data['no_expansion'] = config and config.get('run', 'no_expansion')
                    
                    # Add command and configuration info
                    debug_data['execution_info'] = {
                        'command': original_command,
                        'flags': {
                            'no_expansion': config and config.get('run', 'no_expansion'),
                            'feedback_mode': safety_judge.feedback_mode if safety_judge else False,
                            'test_mode': config and config.get('run', 'test_mode'),
                            'debug': config and config.get('run', 'debug'),
                            'minimal_expansion': config and config.get('run', 'minimal_expansion')
                        }
                    }
                    
                    # Add system prompts to debug output - show both baseline and current
                    debug_data['system_prompts'] = {
                        'baseline_safety_judge': baseline_judge.get_system_prompt() if baseline_judge else safety_judge.get_system_prompt(),
                        'current_safety_judge': safety_judge.get_system_prompt()
                    }
                    
                    # Only include expander if expansion was actually used
                    if not (config and config.get('run', 'no_expansion')):
                        debug_data['system_prompts']['expander'] = expander.get_system_prompt()
                    json.dump(debug_data, f, indent=2, ensure_ascii=False)
                
                # Save EXACT prompts sent to LLM as raw text files
                baseline_prompt_file = debug_dir / f"{prompt_data.id}_baseline_prompt.txt"
                with open(baseline_prompt_file, 'w', encoding='utf-8') as f:
                    f.write("=== BASELINE SAFETY CLASSIFICATION ===\n")
                    f.write(f"System Prompt:\n{baseline_judge.get_system_prompt()}\n\n")
                    f.write(f"User Prompt:\n")
                    user_prompt = SAFETY_USER_TEMPLATE.format(prompt_text=prompt_data.text)
                    f.write(user_prompt)
                    f.write(f"\n\n=== LLM RESPONSE ===\n{original_judgement.raw_response}")
                
                modified_prompt_file = debug_dir / f"{prompt_data.id}_modified_prompt.txt"
                with open(modified_prompt_file, 'w', encoding='utf-8') as f:
                    f.write("=== MODIFIED SAFETY CLASSIFICATION ===\n")
                    f.write(f"System Prompt:\n{safety_judge.get_system_prompt()}\n\n")
                    f.write(f"User Prompt:\n")
                    if safety_judge.feedback_mode:
                        template = SAFETY_FEEDBACK_USER_TEMPLATE
                    else:
                        template = SAFETY_USER_TEMPLATE
                    
                    if config and config.get('run', 'no_expansion'):
                        user_prompt = template.format(prompt_text=prompt_data.text)
                    else:
                        user_prompt = template.format(prompt_text=expanded_text)
                    f.write(user_prompt)
                    f.write(f"\n\n=== LLM RESPONSE ===\n{expanded_judgement.raw_response}")
                
                # If expansion occurred, save expansion prompt too
                if not (config and config.get('run', 'no_expansion')):
                    expansion_prompt_file = debug_dir / f"{prompt_data.id}_expansion_prompt.txt"
                    with open(expansion_prompt_file, 'w', encoding='utf-8') as f:
                        f.write("=== PROMPT EXPANSION ===\n")
                        f.write(f"System Prompt:\n{expander.get_system_prompt()}\n\n")
                        f.write(f"User Prompt:\n{prompt_data.text}\n")
                        f.write(f"\n=== LLM RESPONSE ===\n{expanded_text}")
            
            # Show progress
            orig_label = original_judgement.label
            if no_expansion_mode:
                # In no-expansion mode, show single classification
                print(f"  ✓ {orig_label} ({original_judgement.score:.2f})")
            else:
                # Normal mode with expansion comparison
                exp_label = expanded_judgement.label
                delta = result.score_delta
                change_indicator = " ⚠️" if result.label_changed else ""
                print(f"  ✓ {orig_label}→{exp_label} (Δ{delta:+.2f}){change_indicator}")
            
        except Exception as e:
            print(f"  ✗ Error processing {prompt_data.id}: {e}")
            # Continue processing other prompts
            continue
    
    return results


if __name__ == '__main__':
    main()
