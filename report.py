"""Report generation for PromptExpand results."""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class PromptResult:
    """Container for a single prompt's complete analysis result."""
    
    def __init__(self, id: str, original_prompt: str, original_judgement: Dict,
                 expanded_prompt: str, expanded_judgement: Dict, 
                 model_safety: str, model_expand: str, latency_ms: Dict, no_expansion: bool = False):
        self.id = id
        self.original_prompt = original_prompt
        self.original_judgement = original_judgement
        self.expanded_prompt = expanded_prompt
        self.expanded_judgement = expanded_judgement
        self.model_safety = model_safety
        self.model_expand = model_expand
        self.latency_ms = latency_ms
        self.no_expansion = no_expansion
        
        # Calculate deltas
        self.score_delta = expanded_judgement['score'] - original_judgement['score']
        self.label_changed = original_judgement['label'] != expanded_judgement['label']
        
        # In no-expansion mode without feedback, there's no meaningful comparison
        if no_expansion and not expanded_judgement.get('feedback'):
            self.score_delta = 0.0
            self.label_changed = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/CSV export."""
        result = {
            'id': self.id,
            'original_prompt': self.original_prompt,
            'original_judgement': self.original_judgement,
            'meta': {
                'model_safety': self.model_safety,
                'model_expand': self.model_expand,
                'timestamp_utc': datetime.utcnow().isoformat(),
                'latency_ms': self.latency_ms,
                'no_expansion': self.no_expansion
            }
        }
        
        if self.no_expansion:
            # In no-expansion mode, don't include misleading "expanded" fields
            result['mode'] = 'no_expansion'
        else:
            # Normal expansion mode
            result['expanded_prompt'] = self.expanded_prompt
            result['expanded_judgement'] = self.expanded_judgement
            result['deltas'] = {
                'score_delta': self.score_delta,
                'label_changed': self.label_changed
            }
            result['mode'] = 'expansion'
        
        return result


class ReportGenerator:
    """Generates comprehensive reports from PromptExpand results."""
    
    def __init__(self, output_dir: str, redact: bool = False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.redact = redact
    
    def generate_reports(self, results: List[PromptResult], 
                        write_csv: bool = True, write_jsonl: bool = True):
        """Generate all report formats."""
        # Generate Markdown report
        self._generate_markdown_report(results)
        
        # Generate JSONL output
        if write_jsonl:
            self._generate_jsonl_report(results)
        
        # Generate CSV output
        if write_csv:
            self._generate_csv_report(results)
    
    def _generate_markdown_report(self, results: List[PromptResult]):
        """Generate the main Markdown report."""
        report_path = self.output_dir / 'report.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            # Header
            f.write("# Prompt Safety Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.utcnow().isoformat()}Z\n\n")
            
            if results:
                no_expansion_mode = results[0].no_expansion
                has_feedback = any(r.expanded_judgement.get('feedback') for r in results)
                
                # Mode description
                if no_expansion_mode:
                    if has_feedback:
                        f.write(f"* **Mode:** No Expansion + Feedback Mode (Baseline vs Suspicious System Prompt)\n")
                    else:
                        f.write(f"* **Mode:** No Expansion (Raw Prompt Classification Only)\n")
                else:
                    f.write(f"* **Mode:** Expansion (Original vs Expanded Prompt Comparison)\n")
                
                # Models
                f.write(f"* **Model:** Safety: {results[0].model_safety}")
                if not no_expansion_mode:
                    f.write(f", Expand: {results[0].model_expand}")
                f.write("\n")
                
                # Add command if available (from JSON debug data)
                if hasattr(self, '_execution_info') and self._execution_info:
                    f.write(f"* **Command:** `{self._execution_info.get('command', 'N/A')}`\n")
                    
                    # Add flags summary
                    flags = self._execution_info.get('flags', {})
                    active_flags = [flag for flag, value in flags.items() if value]
                    if active_flags:
                        f.write(f"* **Active Flags:** {', '.join(active_flags)}\n")
                
                f.write("\n")
            
            # Summary metrics
            metrics = self._calculate_metrics(results)
            f.write("## Summary Metrics\n\n")
            f.write(f"- **Total Prompts:** {metrics['total_prompts']}\n")
            f.write(f"- **Safe:** {metrics['original_safe']} ({metrics['original_safe_pct']:.1f}%)\n")
            f.write(f"- **Unsafe:** {metrics['original_unsafe']} ({metrics['original_unsafe_pct']:.1f}%)\n")
            
            # Show expanded/feedback metrics if we have comparison data
            has_feedback = any(r.expanded_judgement.get('feedback') for r in results)
            show_comparison = not results[0].no_expansion or has_feedback
            
            if show_comparison:
                if results[0].no_expansion and has_feedback:
                    f.write(f"- **Feedback Safe:** {metrics['expanded_safe']} ({metrics['expanded_safe_pct']:.1f}%)\n")
                    f.write(f"- **Feedback Unsafe:** {metrics['expanded_unsafe']} ({metrics['expanded_unsafe_pct']:.1f}%)\n")
                else:
                    f.write(f"- **Expanded Safe:** {metrics['expanded_safe']} ({metrics['expanded_safe_pct']:.1f}%)\n")
                    f.write(f"- **Expanded Unsafe:** {metrics['expanded_unsafe']} ({metrics['expanded_unsafe_pct']:.1f}%)\n")
                f.write(f"- **Label Changes:** {metrics['label_changes']} ({metrics['label_change_pct']:.1f}%)\n")
            f.write("\n")
            
            # Confusion matrix (for expansion mode OR no-expansion + feedback mode)
            if show_comparison:
                if results[0].no_expansion and has_feedback:
                    f.write("## Safety Classification Changes (Baseline → Feedback)\n\n")
                    f.write("| Baseline → Feedback | Count |\n")
                else:
                    f.write("## Safety Classification Changes\n\n")
                    f.write("| Original → Expanded | Count |\n")
                f.write("|---------------------|-------|\n")
                f.write(f"| Safe → Safe | {metrics['safe_to_safe']} |\n")
                f.write(f"| Safe → Unsafe | {metrics['safe_to_unsafe']} |\n")
                f.write(f"| Unsafe → Safe | {metrics['unsafe_to_safe']} |\n")
                f.write(f"| Unsafe → Unsafe | {metrics['unsafe_to_unsafe']} |\n\n")
            
            # Results table (first 50)
            f.write("## Results Table\n\n")
            
            if results[0].no_expansion:
                # Check if we have feedback mode (comparison between baseline and feedback)
                has_feedback = any(r.expanded_judgement.get('feedback') for r in results)
                
                if has_feedback:
                    # Feedback mode - show baseline vs feedback comparison
                    f.write("| ID | Baseline | Feedback | Score Δ | Changed | Prompt Preview |\n")
                    f.write("|----|----------|----------|---------|---------|----------------|\n")
                    
                    for result in results[:50]:
                        baseline_label = result.original_judgement['label']
                        baseline_score = result.original_judgement['score']
                        feedback_label = result.expanded_judgement['label']
                        feedback_score = result.expanded_judgement['score']
                        
                        score_delta = feedback_score - baseline_score
                        label_changed = baseline_label != feedback_label
                        change_indicator = "✓" if label_changed else ""
                        
                        # Truncate prompt for preview
                        if self.redact:
                            prompt_preview = f"[REDACTED-{len(result.original_prompt)}chars]"
                        else:
                            prompt_preview = result.original_prompt[:100]
                            if len(result.original_prompt) > 100:
                                prompt_preview += "..."
                            prompt_preview = prompt_preview.replace('|', '\\|').replace('\n', ' ')
                        
                        f.write(f"| {result.id} | {baseline_label} ({baseline_score:.2f}) | "
                               f"{feedback_label} ({feedback_score:.2f}) | {score_delta:+.2f} | "
                               f"{change_indicator} | {prompt_preview} |\n")
                else:
                    # Pure baseline mode - single score
                    f.write("| ID | Classification | Score | Prompt Preview |\n")
                    f.write("|----|---------------|-------|----------------|\n")
                    
                    for result in results[:50]:
                        baseline_label = result.original_judgement['label']
                        baseline_score = result.original_judgement['score']
                        
                        # Truncate prompt for preview
                        if self.redact:
                            prompt_preview = f"[REDACTED-{len(result.original_prompt)}chars]"
                        else:
                            prompt_preview = result.original_prompt[:100]
                            if len(result.original_prompt) > 100:
                                prompt_preview += "..."
                            prompt_preview = prompt_preview.replace('|', '\\|').replace('\n', ' ')
                        
                        f.write(f"| {result.id} | {baseline_label} | {baseline_score:.2f} | {prompt_preview} |\n")
            else:
                f.write("| ID | Original | Expanded | Score Δ | Changed | Prompt Preview |\n")
                f.write("|----|----------|----------|---------|---------|----------------|\n")
                
                for result in results[:50]:
                    original_label = result.original_judgement['label']
                    original_score = result.original_judgement['score']
                    expanded_label = result.expanded_judgement['label']
                    expanded_score = result.expanded_judgement['score']
                    
                    # Truncate prompt for preview
                    if self.redact:
                        prompt_preview = f"[REDACTED-{len(result.original_prompt)}chars]"
                    else:
                        prompt_preview = result.original_prompt[:100]
                        if len(result.original_prompt) > 100:
                            prompt_preview += "..."
                        prompt_preview = prompt_preview.replace('|', '\\|').replace('\n', ' ')
                    
                    changed_icon = "✓" if result.label_changed else ""
                    
                    f.write(f"| {result.id} | {original_label} ({original_score:.2f}) | "
                           f"{expanded_label} ({expanded_score:.2f}) | {result.score_delta:+.2f} | "
                           f"{changed_icon} | {prompt_preview} |\n")
            
            if len(results) > 50:
                f.write(f"\n*Showing first 50 of {len(results)} results. See results.jsonl for complete data.*\n")
            
            # Top outliers or detailed results
            if results[0].no_expansion:
                has_feedback = any(r.expanded_judgement.get('feedback') for r in results)
                
                if has_feedback:
                    f.write("\n## Detailed Results (Baseline vs Feedback)\n\n")
                    for i, result in enumerate(results[:5], 1):
                        f.write(f"### {i}. {result.id}\n\n")
                        
                        baseline_label = result.original_judgement['label']
                        baseline_score = result.original_judgement['score']
                        feedback_label = result.expanded_judgement['label']
                        feedback_score = result.expanded_judgement['score']
                        score_delta = feedback_score - baseline_score
                        
                        f.write(f"**Baseline:** {baseline_label} ({baseline_score:.2f})\n")
                        f.write(f"**Feedback Mode:** {feedback_label} ({feedback_score:.2f})\n")
                        f.write(f"**Score Delta:** {score_delta:+.2f}\n\n")
                        
                        feedback = result.expanded_judgement.get('feedback', '')
                        if feedback:
                            f.write(f"**Feedback:** {feedback}\n\n")
                        
                        if not self.redact:
                            f.write(f"**Prompt:** {result.original_prompt[:300]}{'...' if len(result.original_prompt) > 300 else ''}\n\n")
                        else:
                            f.write("**Prompt:** [REDACTED]\n\n")
                else:
                    f.write("\n## Detailed Results\n\n")
                    for i, result in enumerate(results[:5], 1):
                        f.write(f"### {i}. {result.id}\n\n")
                        f.write(f"**Classification:** {result.original_judgement['label']} ({result.original_judgement['score']:.2f})\n\n")
                        
                        if not self.redact:
                            f.write(f"**Prompt:** {result.original_prompt[:300]}{'...' if len(result.original_prompt) > 300 else ''}\n\n")
                        else:
                            f.write("**Prompt:** [REDACTED]\n\n")
            else:
                f.write("\n## Top Score Changes\n\n")
                outliers = sorted(results, key=lambda r: abs(r.score_delta), reverse=True)[:5]
                
                for i, result in enumerate(outliers, 1):
                    f.write(f"### {i}. {result.id} (Δ{result.score_delta:+.2f})\n\n")
                    f.write(f"**Original:** {result.original_judgement['label']} ({result.original_judgement['score']:.2f})\n")
                    f.write(f"**Expanded:** {result.expanded_judgement['label']} ({result.expanded_judgement['score']:.2f})\n\n")
                    
                    if not self.redact:
                        f.write(f"**Original Prompt:** {result.original_prompt[:200]}{'...' if len(result.original_prompt) > 200 else ''}\n\n")
                        f.write(f"**Expanded Prompt:** {result.expanded_prompt[:200]}{'...' if len(result.expanded_prompt) > 200 else ''}\n\n")
                    else:
                        f.write("**Prompts:** [REDACTED]\n\n")
            
            # Error summary
            parse_errors = sum(1 for r in results if r.original_judgement.get('parse_error') or r.expanded_judgement.get('parse_error'))
            if parse_errors > 0:
                f.write(f"## Errors\n\n")
                f.write(f"- **Parse Errors:** {parse_errors} prompts had JSON parsing issues\n\n")
    
    def _generate_jsonl_report(self, results: List[PromptResult]):
        """Generate JSONL output file."""
        jsonl_path = self.output_dir / 'results.jsonl'
        
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for result in results:
                json.dump(result.to_dict(), f, ensure_ascii=False)
                f.write('\n')
    
    def _generate_csv_report(self, results: List[PromptResult]):
        """Generate CSV output file."""
        csv_path = self.output_dir / 'results.csv'
        
        if not results:
            return
        
        # Dynamic fieldnames based on mode
        if results[0].no_expansion:
            has_feedback = any(r.expanded_judgement.get('feedback') for r in results)
            
            if has_feedback:
                # Feedback mode - show baseline vs feedback comparison
                fieldnames = [
                    'id', 'baseline_label', 'baseline_score', 'feedback_label', 'feedback_score',
                    'score_delta', 'label_changed', 'model_safety', 'latency_judge_ms'
                ]
                if not self.redact:
                    fieldnames.extend(['prompt', 'feedback'])
            else:
                # Pure baseline mode
                fieldnames = [
                    'id', 'label', 'score', 'model_safety',
                    'latency_judge_ms'
                ]
                if not self.redact:
                    fieldnames.extend(['prompt'])
        else:
            fieldnames = [
                'id', 'original_label', 'original_score', 'expanded_label', 'expanded_score',
                'score_delta', 'label_changed', 'model_safety', 'model_expand',
                'latency_judge_original', 'latency_expand', 'latency_judge_expanded'
            ]
            if not self.redact:
                fieldnames.extend(['original_prompt', 'expanded_prompt'])
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                if results[0].no_expansion:
                    has_feedback = any(r.expanded_judgement.get('feedback') for r in results)
                    
                    if has_feedback:
                        # Feedback mode - baseline vs feedback comparison
                        baseline_label = result.original_judgement['label']
                        baseline_score = result.original_judgement['score']
                        feedback_label = result.expanded_judgement['label']
                        feedback_score = result.expanded_judgement['score']
                        score_delta = feedback_score - baseline_score
                        label_changed = baseline_label != feedback_label
                        
                        row = {
                            'id': result.id,
                            'baseline_label': baseline_label,
                            'baseline_score': baseline_score,
                            'feedback_label': feedback_label,
                            'feedback_score': feedback_score,
                            'score_delta': score_delta,
                            'label_changed': label_changed,
                            'model_safety': result.model_safety,
                            'latency_judge_ms': result.latency_ms.get('judge_original', 0)
                        }
                        
                        if not self.redact:
                            row['prompt'] = result.original_prompt
                            row['feedback'] = result.expanded_judgement.get('feedback', '')
                    else:
                        # Pure baseline mode
                        row = {
                            'id': result.id,
                            'label': result.original_judgement['label'],
                            'score': result.original_judgement['score'],
                            'model_safety': result.model_safety,
                            'latency_judge_ms': result.latency_ms.get('judge_original', 0)
                        }
                        
                        if not self.redact:
                            row['prompt'] = result.original_prompt
                else:
                    row = {
                        'id': result.id,
                        'original_label': result.original_judgement['label'],
                        'original_score': result.original_judgement['score'],
                        'expanded_label': result.expanded_judgement['label'],
                        'expanded_score': result.expanded_judgement['score'],
                        'score_delta': result.score_delta,
                        'label_changed': result.label_changed,
                        'model_safety': result.model_safety,
                        'model_expand': result.model_expand,
                        'latency_judge_original': result.latency_ms.get('judge_original', 0),
                        'latency_expand': result.latency_ms.get('expand', 0),
                        'latency_judge_expanded': result.latency_ms.get('judge_expanded', 0)
                    }
                    
                    if not self.redact:
                        row['original_prompt'] = result.original_prompt
                        row['expanded_prompt'] = result.expanded_prompt
                
                writer.writerow(row)
    
    def _calculate_metrics(self, results: List[PromptResult]) -> Dict[str, Any]:
        """Calculate summary metrics from results."""
        if not results:
            return {}
        
        total = len(results)
        original_safe = sum(1 for r in results if r.original_judgement['label'] == 'safe')
        original_unsafe = total - original_safe
        expanded_safe = sum(1 for r in results if r.expanded_judgement['label'] == 'safe')
        expanded_unsafe = total - expanded_safe
        label_changes = sum(1 for r in results if r.label_changed)
        
        # Confusion matrix
        safe_to_safe = sum(1 for r in results if r.original_judgement['label'] == 'safe' and r.expanded_judgement['label'] == 'safe')
        safe_to_unsafe = sum(1 for r in results if r.original_judgement['label'] == 'safe' and r.expanded_judgement['label'] == 'unsafe')
        unsafe_to_safe = sum(1 for r in results if r.original_judgement['label'] == 'unsafe' and r.expanded_judgement['label'] == 'safe')
        unsafe_to_unsafe = sum(1 for r in results if r.original_judgement['label'] == 'unsafe' and r.expanded_judgement['label'] == 'unsafe')
        
        return {
            'total_prompts': total,
            'original_safe': original_safe,
            'original_unsafe': original_unsafe,
            'original_safe_pct': (original_safe / total) * 100,
            'original_unsafe_pct': (original_unsafe / total) * 100,
            'expanded_safe': expanded_safe,
            'expanded_unsafe': expanded_unsafe,
            'expanded_safe_pct': (expanded_safe / total) * 100,
            'expanded_unsafe_pct': (expanded_unsafe / total) * 100,
            'label_changes': label_changes,
            'label_change_pct': (label_changes / total) * 100,
            'safe_to_safe': safe_to_safe,
            'safe_to_unsafe': safe_to_unsafe,
            'unsafe_to_safe': unsafe_to_safe,
            'unsafe_to_unsafe': unsafe_to_unsafe
        }
