# ai_helper.py
# https://platform.openai.com/docs/models

from openai import OpenAI
import os
from dotenv import load_dotenv
import google.generativeai as genai
from anthropic import Anthropic

load_dotenv()  # This will load environment variables from the .env file

# Create an OpenAI client instance
# Ensure you've set your OpenAI API key
client = None
try:
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
except Exception:
    # Will be initialized when needed if API key is available
    pass

# Adding the possibility of using the Gemini API
g_api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=g_api_key)

# Configure Anthropic client for Claude
anthropic_client = None
try:
    anthropic_client = Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
except Exception:
    # Will be initialized when needed if API key is available
    pass


# --- Define Model Configurations ---
#
_model_config = {
    "gpt-4o": lambda prompt: send_prompt_oai(
        prompt=prompt,
        model="gpt-4o",
        max_tokens=16384,
        temperature=0.7,
        role_description="You are an information security expert."
    ),
    "gpt-4o-mini": lambda prompt: send_prompt_oai(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=4096,
        temperature=0.7,
        role_description="You are an information security expert."
    ),
    "o1": lambda prompt: send_prompt_o1(prompt, model="o1"),
    "o1-mini": lambda prompt: send_prompt_o1(prompt, model="o1-mini"),
    "o3": lambda prompt: send_prompt_o1(prompt, model="o3"),
    "o4-mini": lambda prompt: send_prompt_o1(prompt, model="o4-mini"),
    "gpt-5": lambda prompt: send_prompt_o1(prompt, model="gpt-5"),
    "gpt-5.2": lambda prompt: send_prompt_o1(prompt, model="gpt-5.2"),
    "gpt-5.2-codex": lambda prompt: send_prompt_o1(prompt, model="gpt-5.2-codex"),
    "gpt-5.3-codex": lambda prompt: send_prompt_o1(prompt, model="gpt-5.3-codex"),
    "gpt-5.4": lambda prompt: send_prompt_o1(prompt, model="gpt-5.4"),
    "gpt-5.4-mini": lambda prompt: send_prompt_o1(prompt, model="gpt-5.4-mini"),
    "gemini-1.5-pro-latest": lambda prompt: send_prompt_gemini(
        prompt=prompt,
        model_name="gemini-1.5-pro-latest",
        max_output_tokens=8192,
        temperature=0.7,
        top_p=1,
        top_k=40
    ),
    "gemini-2.0-pro-exp-02-05": lambda prompt: send_prompt_gemini(
         prompt=prompt,
         model_name="gemini-2.0-pro-exp-02-05",
         max_output_tokens=8192,
         temperature=0.7,
         top_p=1,
         top_k=40
    ),
    "gemini-2.5-pro-exp-03-25": lambda prompt: send_prompt_gemini(
         prompt=prompt,
         model_name="gemini-2.5-pro-exp-03-25",
         max_output_tokens=8192,
         temperature=0.7,
    ),
    "gemini-3-flash-preview": lambda prompt: send_prompt_gemini(
         prompt=prompt,
         model_name="gemini-3-flash-preview",
         max_output_tokens=4096,
         temperature=0.7,
    ),
    "gemini-3-pro-preview": lambda prompt: send_prompt_gemini(
         prompt=prompt,
         model_name="gemini-3-pro-preview",
         max_output_tokens=8192,
         temperature=0.7,
    ),
    "gemini-3.1-pro-preview": lambda prompt: send_prompt_gemini(
         prompt=prompt,
         model_name="gemini-3.1-pro-preview",
         max_output_tokens=8192,
         temperature=0.7,
    ),
    "gemini-2.0-flash": lambda prompt: send_prompt_gemini(
         prompt=prompt,
         model_name="gemini-2.0-flash",
         max_output_tokens=4096,
         temperature=0.7,
    ),
    "claude-3-5-sonnet": lambda prompt: send_prompt_claude(
         prompt=prompt,
         model="claude-3-5-sonnet-20241022",
         max_tokens=4096,
         temperature=1.0
    ),
    "claude-3-7-sonnet": lambda prompt: send_prompt_claude(
         prompt=prompt,
         model="claude-3-7-sonnet-20250219",
         max_tokens=4096,
         temperature=0.7
    ),
    "claude-sonnet-4.6": lambda prompt: send_prompt_claude(
         prompt=prompt,
         model="claude-sonnet-4-6-20250610",
         max_tokens=4096,
         temperature=0.7
    ),
    "claude-opus-4.6": lambda prompt: send_prompt_claude(
         prompt=prompt,
         model="claude-opus-4-6-20250610",
         max_tokens=4096,
         temperature=0.7
    ),
    "claude-haiku-4.5": lambda prompt: send_prompt_claude(
         prompt=prompt,
         model="claude-haiku-4-5-20251001",
         max_tokens=4096,
         temperature=0.7
    ),
    "claude-3-5-haiku": lambda prompt: send_prompt_claude(
         prompt=prompt,
         model="claude-3-5-haiku-20241022",
         max_tokens=4096,
         temperature=0.7
    ),
    # CLI backends (no API keys required - uses local CLI tools)
    # Claude CLI: default (opus), sonnet, haiku
    "claude-cli": lambda prompt: _send_prompt_cli("claude-cli", prompt),
    "claude-cli-sonnet": lambda prompt: _send_prompt_cli("claude-cli", prompt, model="claude-sonnet-4-6"),
    "claude-cli-haiku": lambda prompt: _send_prompt_cli("claude-cli", prompt, model="claude-haiku-4-5"),
    # Gemini CLI: 3-flash (default), 3-pro, 3.1-pro, 2.5-pro
    "gemini-cli": lambda prompt: _send_prompt_cli("gemini-cli", prompt),
    "gemini-cli-pro": lambda prompt: _send_prompt_cli("gemini-cli", prompt, model="gemini-3-pro-preview"),
    "gemini-cli-3.1-pro": lambda prompt: _send_prompt_cli("gemini-cli", prompt, model="gemini-3.1-pro-preview"),
    "gemini-cli-2.5-pro": lambda prompt: _send_prompt_cli("gemini-cli", prompt, model="gemini-2.5-pro"),
    # Codex CLI: gpt-5.4 (default), gpt-5.4-mini, gpt-5.3-codex, gpt-5.2-codex, gpt-5.2
    "codex": lambda prompt: _send_prompt_cli("codex", prompt),
    "codex-mini": lambda prompt: _send_prompt_cli("codex", prompt, model="gpt-5.4-mini"),
    "codex-5.3": lambda prompt: _send_prompt_cli("codex", prompt, model="gpt-5.3-codex"),
    "codex-5.2": lambda prompt: _send_prompt_cli("codex", prompt, model="gpt-5.2-codex"),
}
# --- End Model Configurations ---


def _send_prompt_cli(backend: str, prompt: str, model: str = None) -> str:
    """Route to CLI backend. Lazy-imports to avoid errors when CLI tools aren't installed."""
    from cli_backends import send_prompt_cli
    return send_prompt_cli(prompt, backend=backend, model=model)

def get_supported_models():
    """Returns a list of supported model names."""
    return list(_model_config.keys())

def send_prompt(prompt, model=None):
    if model is None:
        from config import DEFAULT_MODEL
        model = DEFAULT_MODEL
    """Sends a prompt to the specified AI model."""
    # Check if the model is supported
    if model not in _model_config:
        # Try adding '-latest' if applicable (e.g., for gemini-1.5-pro)
        if f"{model}-latest" in _model_config:
             model = f"{model}-latest"
        else:
             supported_models = get_supported_models()
             raise ValueError(f"Unsupported model: {model}. Supported models are: {supported_models}")


    print(f"Attempting to use model: {model}")
    # Call the corresponding function by looking up the dictionary
    try:
        return _model_config[model](prompt)
    except Exception as e:
        print(f"Error calling model '{model}': {e}")
        # Optionally, implement fallback logic here or re-raise
        raise # Re-raise the exception for now


# Send prompts with GPT4o and 4o-mini
def send_prompt_oai(prompt, model=None, max_tokens=1500, temperature=0.7,
                role_description="You are an information security expert."):
    if model is None:
        from config import DEFAULT_MODEL
        model = DEFAULT_MODEL
    # Initialize client if needed
    global client
    if client is None:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Make the chat completion request using the OpenAI client
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": role_description},
            {"role": "user", "content": prompt},
        ],
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    print("model used: ", model)
    # Extract the generated text from the response
    content = response.choices[0].message.content

    return content

# Send prompts with o1 models
# model="o1-preview"
# model="o1-mini",
def send_prompt_o1(prompt, model="o1-mini"):
    # Initialize client if needed
    global client
    if client is None:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
            "role": "user",
            "content": prompt
            }
        ]
    )

    print("Used model: ", model)
    content = response.choices[0].message.content

    return content


def send_prompt_gemini(prompt, model_name="gemini-2.5-pro", max_output_tokens=1024, temperature=0.9, top_p=1, top_k=1):
    """
    Sends a prompt to the Gemini API and returns the response.

    Args:
        prompt: The text prompt to send.
        model_name: The name of the Gemini model to use (e.g., "gemini-pro").
        max_output_tokens: The maximum number of tokens to generate.
        temperature: Controls the randomness of the output.
        top_p: Controls the diversity of the output.
        top_k: Controls the diversity of the output (similar to top_p).
    Returns:
        The generated text, or None if there was an error.
    """

    model = genai.GenerativeModel(model_name)

    generation_config = genai.types.GenerationConfig(
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k
    )


    try:
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            stream=False
        )

        print("Used model: ", model)

        return response.text
    except Exception as e:
        print(f"Error generating content: {e}")
        return None


def send_prompt_claude(prompt, model="claude-3-sonnet-20240229", max_tokens=4096, temperature=0.7,
                     role_description="You are an information security expert."):
    """
    Sends a prompt to Anthropic's Claude API and returns the generated text.
    
    Args:
        prompt: The text prompt to send.
        model: The Claude model to use (e.g., "claude-3-opus-20240229").
        max_tokens: Maximum number of tokens to generate.
        temperature: Controls randomness of generations.
        role_description: System prompt that sets the context for the model.
        
    Returns:
        The generated text, or None if there was an error.
    """
    # Initialize client if needed
    global anthropic_client
    if anthropic_client is None:
        anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    try:
        # Create a message with system and user content
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=role_description,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        print("Used model: ", model)
        
        # Extract the content from the response
        return response.content[0].text
        
    except Exception as e:
        print(f"Error generating content with Claude: {e}")
        return None

