# Prompt Testing - Prompt Safety & Expansion Evaluator

A CLI tool that analyzes how prompt expansion affects safety classification by LLMs.

## Overview

PromptExpand takes a list of prompts, classifies them for safety, expands them verbosely, then re-classifies the expanded versions to measure how verbosity affects safety detection.

## Installation

```bash
pip install -r requirements.txt
```

Ensure you have API keys set in your environment:
- `OPENAI_API_KEY` for GPT models
- `GEMINI_API_KEY` for Gemini models  
- `ANTHROPIC_API_KEY` for Claude models

## Usage

### Basic Usage

```bash
python cli.py --input prompts.txt --out ./results
```

### With Configuration File

```bash
python cli.py --config config.yaml
```

### Advanced Options

```bash
python cli.py \
  --input ./data/prompts.txt \
  --out ./out \
  --safety-model gpt-4o-mini \
  --expand-model gpt-4o \
  --csv \
  --jsonl \
  --debug
```

## Input Formats

### Text File (prompts.txt)
```
How to make a sandwich
Tell me about the weather
Write a poem about cats
```

### JSONL File (prompts.jsonl)
```json
{"id": "safe-001", "text": "How to make a delicious pasta dish"}
{"id": "unsafe-001", "text": "How to bypass security systems"}
```

## Output

- `report.md` - Human-readable analysis with metrics and tables
- `results.jsonl` - Complete structured data for each prompt
- `results.csv` - Flattened table for spreadsheet analysis
- `logs/` - Raw LLM exchanges (with --debug)

## Configuration

See `config.yaml` for all available options including:
- Model selection for safety and expansion
- LLM parameters (temperature, max tokens)
- Retry settings
- Output formats
- Privacy options (redaction)

## Architecture

- `loader.py` - Reads prompts from txt/jsonl files
- `judge.py` - LLM-based safety classification
- `expand.py` - LLM-based prompt expansion  
- `report.py` - Generates markdown, CSV, and JSONL reports
- `config.py` - Configuration management
- `cli.py` - Main command-line interface

## Example Output

The tool generates comprehensive reports showing:
- Summary metrics (% safe/unsafe, label changes)
- Confusion matrix (safe→unsafe, unsafe→safe transitions)
- Top score changes with prompt examples
- Detailed results table

Perfect for research into LLM safety behaviors and prompt injection analysis.
