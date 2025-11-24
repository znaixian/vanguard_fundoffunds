"""
LLM Client - Supports both Anthropic Claude and Azure OpenAI

Configures and manages connections to either Claude or Azure OpenAI based on settings.
"""

import os
import configparser
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Determine active provider
def get_active_provider():
    """Determine which LLM provider to use"""
    # Priority 1: Environment variable (for local development)
    env_provider = os.getenv('LLM_PROVIDER')
    if env_provider:
        return env_provider.lower()

    # Priority 2: config.ini (for FactSet.io deployment)
    config_path = Path(os.getenv('PROJECT_ROOT', os.getcwd())) / 'config' / 'config.ini'
    if config_path.exists():
        config = configparser.ConfigParser()
        config.read(config_path)
        if 'LLMProvider' in config:
            return config['LLMProvider'].get('active_provider', 'anthropic').lower()

    # Default: Anthropic
    return 'anthropic'

# Check if running on Streamlit Cloud
def get_streamlit_secrets():
    """Try to get Streamlit secrets if available"""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and st.secrets:
            return st.secrets
    except:
        pass
    return None

ACTIVE_PROVIDER = get_active_provider()

if ACTIVE_PROVIDER == 'azure':
    print(f"[INFO] Using Azure OpenAI as LLM provider")

    from openai import AzureOpenAI
    import httpx

    # Load Azure configuration
    config_path = Path(os.getenv('PROJECT_ROOT', os.getcwd())) / 'config' / 'config.ini'
    config = configparser.ConfigParser()
    config.read(config_path)

    azure_config = config['AzureOpenAI']

    # Set up SSL certificate
    ca_bundle_path = Path(os.getenv('PROJECT_ROOT', os.getcwd())) / 'config' / 'ca-bundle-full.crt'
    http_client = httpx.Client(verify=str(ca_bundle_path)) if ca_bundle_path.exists() else None

    LLM_CLIENT = AzureOpenAI(
        api_key=azure_config.get('api_key'),
        api_version=azure_config.get('api_version', '2023-09-01-preview'),
        azure_endpoint=azure_config.get('endpoint'),
        http_client=http_client
    )

    MODEL = azure_config.get('deployment_name', 'gpt-4')
    MAX_TOKENS = 8000

else:  # anthropic
    print(f"[INFO] Using Anthropic Claude as LLM provider")

    from anthropic import Anthropic

    # Check Streamlit secrets first
    st_secrets = get_streamlit_secrets()

    if st_secrets and 'ANTHROPIC_API_KEY' in st_secrets:
        ANTHROPIC_API_KEY = st_secrets['ANTHROPIC_API_KEY']
        MODEL = st_secrets.get('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
        MAX_TOKENS = int(st_secrets.get('CLAUDE_MAX_TOKENS', '8000'))
    else:
        ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
        MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
        MAX_TOKENS = int(os.getenv('CLAUDE_MAX_TOKENS', '8000'))

    # Verify API key
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == 'your_api_key_here':
        raise ValueError(
            "ANTHROPIC_API_KEY not set. "
            "For local: Add to .env file. "
            "For Streamlit Cloud: Add to Secrets Management. "
            "Get your API key from https://console.anthropic.com"
        )

    LLM_CLIENT = Anthropic(api_key=ANTHROPIC_API_KEY)


def convert_anthropic_tools_to_openai(tools):
    """Convert Anthropic tool format to OpenAI function format"""
    if not tools:
        return None

    openai_functions = []
    for tool in tools:
        openai_func = {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"]
        }
        openai_functions.append(openai_func)

    return openai_functions


def create_message(messages, tools=None, system=None):
    """
    Create a message using the active LLM provider.

    Args:
        messages: List of message dictionaries
        tools: List of tool definitions (Anthropic format)
        system: System prompt string

    Returns:
        Response object from the LLM
    """
    if ACTIVE_PROVIDER == 'azure':
        # Convert Anthropic format to OpenAI format
        openai_messages = []

        # Add system message if provided
        if system:
            openai_messages.append({"role": "system", "content": system})

        # Convert messages
        for msg in messages:
            if msg['role'] == 'user':
                if isinstance(msg['content'], str):
                    openai_messages.append({"role": "user", "content": msg['content']})
                elif isinstance(msg['content'], list):
                    # Handle tool results - convert to function messages
                    for block in msg['content']:
                        if block.get('type') == 'tool_result':
                            # Extract tool name and result
                            content = block.get('content', '')
                            if isinstance(content, dict):
                                content = str(content.get('content', [{}])[0].get('text', ''))
                            elif isinstance(content, list):
                                content = str(content[0].get('text', '')) if content else ''

                            openai_messages.append({
                                "role": "function",
                                "name": block.get('tool_name', 'unknown'),
                                "content": str(content)
                            })
            elif msg['role'] == 'assistant':
                if isinstance(msg['content'], list):
                    # Handle assistant message with potential function calls
                    text_content = ""
                    function_calls = []

                    for block in msg['content']:
                        if hasattr(block, 'text'):
                            text_content += block.text
                        elif isinstance(block, dict):
                            if block.get('type') == 'text':
                                text_content += block.get('text', '')
                            elif block.get('type') == 'tool_use':
                                # This shouldn't happen in Azure flow, but handle it
                                pass

                    if text_content:
                        openai_messages.append({"role": "assistant", "content": text_content})
                elif isinstance(msg['content'], str):
                    openai_messages.append({"role": "assistant", "content": msg['content']})

        # Convert tools to OpenAI functions format
        openai_functions = convert_anthropic_tools_to_openai(tools) if tools else None

        # Call Azure OpenAI with function calling support
        if openai_functions:
            response = LLM_CLIENT.chat.completions.create(
                model=MODEL,
                messages=openai_messages,
                functions=openai_functions,
                function_call="auto",
                temperature=0,
                max_tokens=MAX_TOKENS
            )
        else:
            response = LLM_CLIENT.chat.completions.create(
                model=MODEL,
                messages=openai_messages,
                temperature=0,
                max_tokens=MAX_TOKENS
            )

        return response

    else:  # anthropic
        return LLM_CLIENT.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0,
            system=system,
            tools=tools,
            messages=messages
        )
