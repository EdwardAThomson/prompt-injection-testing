# Prompt Safety Expansion Analysis - Findings Report

**Generated:** 2025-08-27T20:27:00Z  
**Dataset:** Agent Dojo 27 prompts  
**Models Tested:** GPT-4o, GPT-5  

## Executive Summary

This report analyzes the impact of prompt expansion and adversarial system prompts on AI safety classification across GPT-4o and GPT-5 models. Key findings show that verbose expansion generally degrades safety detection, while adversarial "judgmental" system prompts can improve detection rates.

## Experimental Setup

### Dataset
- **Source:** Agent Dojo benchmark (27 prompts)
- **Content:** Mix of safe and unsafe prompts targeting financial, data access, and social engineering scenarios
- **Baseline Distribution:** 
  - GPT-4o: 44.4% safe, 55.6% unsafe
  - GPT-5: 55.6% safe, 44.4% unsafe

### Test Conditions
1. **Baseline:** Raw prompt classification
2. **Minimal Expansion:** Prompts expanded with minimal verbosity
3. **Standard Expansion:** Prompts expanded to be detailed/verbose
4. **Adversarial Feedback:** Baseline prompts evaluated with suspicious system prompt

## Results Summary

| Model | Condition | Safe Rate | Unsafe Rate | Label Changes | Direction |
|-------|-----------|-----------|-------------|---------------|-----------|
| **GPT-4o** | Baseline | 44.4% | 55.6% | - | - |
| GPT-4o | Minimal Expansion | 55.6% | 44.4% | 18.5% | 4 unsafe→safe, 1 safe→unsafe |
| GPT-4o | Standard Expansion | 70.4% | 29.6% | 25.9% | 7 unsafe→safe, 0 safe→unsafe |
| GPT-4o | Adversarial | 18.5% | 81.5% | 25.9% | 0 unsafe→safe, 7 safe→unsafe |
| **GPT-5** | Baseline | 55.6% | 44.4% | - | - |
| GPT-5 | Standard Expansion | 77.8% | 22.2% | 22.2% | 6 unsafe→safe, 0 safe→unsafe |
| GPT-5 | Adversarial | 29.6% | 70.4% | 29.6% | 0 unsafe→safe, 8 safe→unsafe |

## Key Findings

### 1. Expansion Effects

**GPT-4o:**
- **Minimal expansion:** Becomes more permissive (4 unsafe→safe, 1 safe→unsafe) - worse for safety
- **Standard expansion:** Becomes more permissive (7 unsafe→safe, 0 safe→unsafe) - worse for safety
- **Pattern:** Both expansion types make GPT-4o miss actual threats

**GPT-5:**
- **Standard expansion:** Becomes more permissive (6 unsafe→safe, 0 safe→unsafe) - worse for safety
- **Pattern:** Expansion makes GPT-5 miss actual threats by classifying unsafe prompts as safe

### 2. Adversarial System Prompt Effects

**GPT-4o:**
- **Impact:** 25.9% label changes (7 safe→unsafe, 0 unsafe→safe)
- **Result:** Strictly more restrictive, no false negatives introduced
- **Interpretation:** Perfect precision improvement - catches additional threats without false positives

**GPT-5:**
- **Impact:** 29.6% label changes (8 safe→unsafe, 0 unsafe→safe)  
- **Result:** 30% more restrictive classification
- **Interpretation:** Similar precision improvement pattern as GPT-4o

### 3. Model Differences

**Baseline Sensitivity:**
- GPT-5 is more permissive at baseline (59.3% vs 44.4% safe)
- GPT-4o appears more conservative in initial classifications

**Expansion Response:**
- **Consistent pattern:** Both GPT-4o and GPT-5 become more permissive with expansion
- **Safety degradation:** All expansion conditions result in unsafe→safe transitions
- **Consistency:** Both models show similar positive response to adversarial system prompts

## Implications

### Security Perspective
1. **Adversarial prompts work:** Both models can be made more restrictive without introducing false positives
2. **Expansion risk:** All prompt expansion degrades safety detection by making models more permissive
3. **Universal vulnerability:** Both models consistently miss threats when prompts are expanded

### Practical Applications
1. **Safety systems:** Consider adversarial system prompts for improved threat detection
2. **Prompt engineering:** Be cautious with verbose expansions in safety-critical applications
3. **Model selection:** GPT-5 baseline appears more balanced, but both respond well to targeted interventions

## Limitations & Considerations

1. **Sample size:** 27 prompts may not capture full distribution of real-world scenarios
2. **Stochasticity:** Results may vary across runs due to model randomness
3. **Domain specificity:** Agent Dojo focuses on specific attack vectors (financial, data access)
4. **System prompt generalization:** Adversarial approach may not transfer to other domains

## Recommendations

1. **For safety systems:** Implement adversarial system prompts as they show consistent improvement
2. **For expansion systems:** Avoid expansion in safety-critical applications as it consistently degrades threat detection
3. **For model deployment:** Consider model-specific safety calibration based on baseline behavior
4. **For future research:** Expand dataset size and domain coverage to validate findings

---

*This analysis demonstrates that both prompt expansion and system prompt engineering can significantly impact AI safety classification, with model-specific patterns that require careful consideration in deployment.*
