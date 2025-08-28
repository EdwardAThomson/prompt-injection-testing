#!/usr/bin/env python3
"""
GUI wrapper for PromptExpand CLI tool.
Provides an easy-to-use interface with radio buttons and option validation.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
from pathlib import Path
import json
from ai_helper import get_supported_models


class PromptExpandGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Prompt Safety & Expansion Evaluator")
        self.root.geometry("800x900")
        
        # Variables
        default_input = str(Path(__file__).parent / "prompts_agent_dojo_27.txt")
        self.input_file = tk.StringVar(value=default_input)
        self.output_dir = tk.StringVar(value="test_out")
        
        # Model variables - get from ai_helper
        self.supported_models = get_supported_models()
        self.safety_model = tk.StringVar(value="gpt-4o")
        self.expand_model = tk.StringVar(value="gpt-4o")
        
        # Mode variables
        self.expansion_mode = tk.StringVar(value="normal")  # normal, minimal, none
        self.feedback_mode = tk.BooleanVar(value=False)
        self.test_mode = tk.BooleanVar(value=True)
        self.debug_mode = tk.BooleanVar(value=True)
        
        # Output format variables
        self.generate_csv = tk.BooleanVar(value=True)
        self.generate_jsonl = tk.BooleanVar(value=True)
        self.redact_prompts = tk.BooleanVar(value=False)
        
        # Process tracking
        self.process = None
        self.is_running = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the GUI layout."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Title
        title_label = ttk.Label(main_frame, text="Prompt Safety & Expansion Evaluator", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=row, column=0, columnspan=3, pady=(0, 20))
        row += 1
        
        # Input file selection
        ttk.Label(main_frame, text="Input File:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_file, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_input_file).grid(row=row, column=2, padx=5)
        row += 1
        
        # Output directory
        ttk.Label(main_frame, text="Output Dir:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_dir, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output_dir).grid(row=row, column=2, padx=5)
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Models section
        models_frame = ttk.LabelFrame(main_frame, text="Models", padding="10")
        models_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        models_frame.columnconfigure(1, weight=1)
        
        ttk.Label(models_frame, text="Safety Model:").grid(row=0, column=0, sticky=tk.W, pady=2)
        safety_combo = ttk.Combobox(models_frame, textvariable=self.safety_model, 
                                   values=self.supported_models)
        safety_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Label(models_frame, text="Expand Model:").grid(row=1, column=0, sticky=tk.W, pady=2)
        expand_combo = ttk.Combobox(models_frame, textvariable=self.expand_model,
                                   values=self.supported_models)
        expand_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        row += 1
        
        # Expansion mode section
        expansion_frame = ttk.LabelFrame(main_frame, text="Expansion Mode", padding="10")
        expansion_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Radiobutton(expansion_frame, text="Normal Expansion (verbose rewriting)", 
                       variable=self.expansion_mode, value="normal").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(expansion_frame, text="Minimal Expansion (concise rewriting)", 
                       variable=self.expansion_mode, value="minimal").grid(row=1, column=0, sticky=tk.W)
        ttk.Radiobutton(expansion_frame, text="No Expansion (raw prompts only)", 
                       variable=self.expansion_mode, value="none").grid(row=2, column=0, sticky=tk.W)
        row += 1
        
        # Safety mode section
        safety_frame = ttk.LabelFrame(main_frame, text="Safety Classification Mode", padding="10")
        safety_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Checkbutton(safety_frame, text="Feedback Mode (suspicious system prompt + detailed explanations)", 
                       variable=self.feedback_mode).grid(row=0, column=0, sticky=tk.W)
        
        # Info label
        info_label = ttk.Label(safety_frame, text="ℹ️ Feedback mode uses a suspicious system prompt to detect malicious intent", 
                              foreground="blue", font=("Arial", 9))
        info_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        row += 1
        
        # Runtime options section
        runtime_frame = ttk.LabelFrame(main_frame, text="Runtime Options", padding="10")
        runtime_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Checkbutton(runtime_frame, text="Test Mode (first 5 prompts only)", 
                       variable=self.test_mode).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(runtime_frame, text="Debug Mode (save raw LLM responses)", 
                       variable=self.debug_mode).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        ttk.Checkbutton(runtime_frame, text="Generate CSV output", 
                       variable=self.generate_csv).grid(row=1, column=0, sticky=tk.W)
        ttk.Checkbutton(runtime_frame, text="Generate JSONL output", 
                       variable=self.generate_jsonl).grid(row=1, column=1, sticky=tk.W, padx=(20, 0))
        
        ttk.Checkbutton(runtime_frame, text="Redact prompts in reports", 
                       variable=self.redact_prompts).grid(row=2, column=0, sticky=tk.W)
        row += 1
        
        # Baseline comparison info
        baseline_frame = ttk.LabelFrame(main_frame, text="Baseline Comparison", padding="10")
        baseline_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        baseline_info = ttk.Label(baseline_frame, 
                                 text="💡 Tip: To compare against baseline, run twice:\n" +
                                      "1. First with 'No Expansion' + no feedback mode (baseline)\n" +
                                      "2. Then with your desired settings (test condition)",
                                 foreground="darkgreen", font=("Arial", 9))
        baseline_info.grid(row=0, column=0, sticky=tk.W)
        row += 1
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        self.run_button = ttk.Button(button_frame, text="Run Analysis", command=self.run_analysis)
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_analysis, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Open Output Folder", command=self.open_output_folder).pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Output log
        log_frame = ttk.LabelFrame(main_frame, text="Output Log", padding="5")
        log_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def browse_input_file(self):
        """Browse for input file."""
        filename = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=[("Text files", "*.txt"), ("JSONL files", "*.jsonl"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
    
    def browse_output_dir(self):
        """Browse for output directory."""
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_dir.set(dirname)
    
    def open_output_folder(self):
        """Open the output folder in file manager."""
        output_path = Path(self.output_dir.get())
        if output_path.exists():
            if os.name == 'nt':  # Windows
                os.startfile(output_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['xdg-open', str(output_path)])
        else:
            messagebox.showwarning("Warning", f"Output directory does not exist: {output_path}")
    
    def log_message(self, message):
        """Add message to log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def validate_inputs(self):
        """Validate user inputs."""
        if not self.input_file.get():
            messagebox.showerror("Error", "Please select an input file.")
            return False
        
        if not Path(self.input_file.get()).exists():
            messagebox.showerror("Error", f"Input file does not exist: {self.input_file.get()}")
            return False
        
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please specify an output directory.")
            return False
        
        return True
    
    def build_command(self):
        """Build the CLI command from GUI settings."""
        cmd = ["python", "cli.py"]
        
        # Input and output
        cmd.extend(["--input", self.input_file.get()])
        cmd.extend(["--out", self.output_dir.get()])
        
        # Models
        cmd.extend(["--safety-model", self.safety_model.get()])
        cmd.extend(["--expand-model", self.expand_model.get()])
        
        # Expansion mode
        if self.expansion_mode.get() == "minimal":
            cmd.append("--minimal-expansion")
        elif self.expansion_mode.get() == "none":
            cmd.append("--no-expansion")
        
        # Safety mode
        if self.feedback_mode.get():
            cmd.append("--feedback-mode")
        
        # Runtime options
        if self.test_mode.get():
            cmd.append("--test-mode")
        
        if self.debug_mode.get():
            cmd.append("--debug")
        
        if not self.generate_csv.get():
            cmd.append("--no-csv")
        
        if self.generate_jsonl.get():
            cmd.append("--jsonl")
        
        if self.redact_prompts.get():
            cmd.append("--redact")
        
        return cmd
    
    def run_analysis(self):
        """Run the analysis in a separate thread."""
        if not self.validate_inputs():
            return
        
        if self.is_running:
            messagebox.showwarning("Warning", "Analysis is already running.")
            return
        
        # Build command
        cmd = self.build_command()
        
        # Log the command
        self.log_message(f"Running: {' '.join(cmd)}")
        self.log_message("=" * 50)
        
        # Update UI state
        self.is_running = True
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Run in thread
        thread = threading.Thread(target=self._run_process, args=(cmd,))
        thread.daemon = True
        thread.start()
    
    def _run_process(self, cmd):
        """Run the subprocess and capture output."""
        try:
            # Change to the script directory
            script_dir = Path(__file__).parent
            
            # Activate virtual environment and run
            if os.name == 'posix':  # Linux/macOS
                full_cmd = f"cd {script_dir} && source venv/bin/activate && {' '.join(cmd)}"
                self.process = subprocess.Popen(
                    full_cmd,
                    shell=True,
                    executable='/bin/bash',  # Explicitly use bash for source command
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
            else:  # Windows
                full_cmd = f"cd {script_dir} && venv\\Scripts\\activate && {' '.join(cmd)}"
                self.process = subprocess.Popen(
                    full_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
            
            # Read output line by line
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.root.after(0, self.log_message, line.rstrip())
            
            # Wait for completion
            self.process.wait()
            
            # Update UI
            if self.process.returncode == 0:
                self.root.after(0, self.log_message, "✅ Analysis completed successfully!")
            else:
                self.root.after(0, self.log_message, f"❌ Analysis failed with exit code {self.process.returncode}")
            
        except Exception as e:
            self.root.after(0, self.log_message, f"❌ Error: {str(e)}")
        
        finally:
            # Reset UI state
            self.root.after(0, self._reset_ui_state)
    
    def _reset_ui_state(self):
        """Reset UI state after process completion."""
        self.is_running = False
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.process = None
    
    def stop_analysis(self):
        """Stop the running analysis."""
        if self.process and self.is_running:
            try:
                self.process.terminate()
                self.log_message("🛑 Analysis stopped by user.")
            except Exception as e:
                self.log_message(f"Error stopping process: {str(e)}")
        
        self._reset_ui_state()


def main():
    """Main entry point."""
    root = tk.Tk()
    app = PromptExpandGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
