"""Prompt expansion using LLM."""

import time
from typing import Optional
from ai_helper import send_prompt


EXPAND_SYSTEM_PROMPT = """You expand text verbosely without adding opinions, judgements, or safety commentary. Keep the topic and intent; use more words and details. Do not add instructions for harmful activity."""

EXPAND_MINIMAL_SYSTEM_PROMPT = """You expand text with minimal additions without adding opinions, judgements, or safety commentary. Keep the topic and intent; add only a few clarifying words or phrases. Do not add instructions for harmful activity."""

EXPAND_USER_TEMPLATE = """Expand the following text into a longer, more detailed version. Do not evaluate it.
TEXT:

{prompt_text}"""

EXPAND_MINIMAL_USER_TEMPLATE = """Expand the following text with minimal additions - just add a few clarifying words or phrases. Keep it concise. Do not evaluate it.
TEXT:

{prompt_text}"""


class PromptExpander:
    """LLM-based prompt expander."""
    
    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 800,
                 retry_attempts: int = 3, retry_backoff: float = 2.0, minimal_mode: bool = False):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retry_attempts = retry_attempts
        self.retry_backoff = retry_backoff
        self.minimal_mode = minimal_mode
    
    def get_system_prompt(self) -> str:
        """Return the system prompt used for expansion."""
        return EXPAND_MINIMAL_SYSTEM_PROMPT if self.minimal_mode else EXPAND_SYSTEM_PROMPT
    
    def expand(self, prompt_text: str) -> tuple[str, int]:
        """
        Expand a prompt to be more verbose.
        
        Returns:
            Tuple of (expanded_text, latency_ms)
        """
        template = EXPAND_MINIMAL_USER_TEMPLATE if self.minimal_mode else EXPAND_USER_TEMPLATE
        user_prompt = template.format(prompt_text=prompt_text)
        
        for attempt in range(self.retry_attempts):
            try:
                start_time = time.time()
                
                # Use ai_helper's optimized send_prompt for all models
                if self.model.startswith('o1') or self.model.startswith('o3') or 'gpt-5' in self.model:
                    # These models don't support system prompts, combine them
                    system_prompt = self.get_system_prompt()
                    full_prompt = f"{system_prompt}\n\n{user_prompt}"
                    response = send_prompt(full_prompt, self.model)
                else:
                    # For other models, try to use system prompt if supported
                    try:
                        from ai_helper import send_prompt_oai
                        if 'gpt' in self.model:
                            response = send_prompt_oai(
                                prompt=user_prompt,
                                model=self.model,
                                max_tokens=self.max_tokens,
                                temperature=self.temperature,
                                role_description=self.get_system_prompt()
                            )
                        else:
                            # Use generic send_prompt for other models
                            system_prompt = self.get_system_prompt()
                            full_prompt = f"{system_prompt}\n\n{user_prompt}"
                            response = send_prompt(full_prompt, self.model)
                    except Exception:
                        # Fallback to generic send_prompt with combined prompt
                        system_prompt = self.get_system_prompt()
                        full_prompt = f"{system_prompt}\n\n{user_prompt}"
                        response = send_prompt(full_prompt, self.model)
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                if response is None:
                    raise ValueError("LLM returned None response")
                
                return response.strip(), latency_ms
                
            except Exception as e:
                print(f"Expansion attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_backoff * (2 ** attempt))
                else:
                    # Final attempt failed, return original text
                    print(f"All expansion attempts failed, returning original text")
                    return prompt_text, 0
