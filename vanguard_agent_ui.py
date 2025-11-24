"""
Vanguard Fund Calculation AI Assistant - Streamlit UI

A beautiful web interface for interacting with the Vanguard AI agent.

Usage:
    streamlit run vanguard_agent_ui.py

    or

    python -m streamlit run vanguard_agent_ui.py
"""

import streamlit as st
import os
from datetime import datetime
from pathlib import Path
import re

# Import agent configuration and tools
try:
    from agent.llm_client import LLM_CLIENT, MODEL, MAX_TOKENS, ACTIVE_PROVIDER, create_message
    from agent.config import TOOLS, SYSTEM_PROMPT
    from agent.main import execute_tool
    print(f"[INFO] Agent modules loaded successfully. Provider: {ACTIVE_PROVIDER}, Model: {MODEL}, Tools: {len(TOOLS)}")
except Exception as e:
    print(f"[ERROR] Failed to import agent modules: {e}")
    raise

# Helper functions
def extract_output_paths(text: str) -> list:
    """Extract output file paths from tool result text."""
    paths = []
    # Pattern to match: "  Output: path/to/file.csv" (with optional leading whitespace)
    pattern = r'\s*Output:\s*([^\n]+\.csv)'
    matches = re.findall(pattern, text)
    print(f"[DEBUG] extract_output_paths called with text length: {len(text)}")
    print(f"[DEBUG] Text content:\n{text[:500]}...")  # First 500 chars
    print(f"[DEBUG] Found {len(matches)} matches: {matches}")
    for match in matches:
        path = Path(match.strip())
        print(f"[DEBUG] Checking path: {path} (exists: {path.exists()})")
        if path.exists():
            paths.append(path)
            print(f"[DEBUG] Added path: {path}")
    print(f"[DEBUG] Total paths extracted: {len(paths)}")
    return paths

def display_download_section(output_files: list):
    """Display download buttons for output files."""
    if not output_files:
        return

    st.markdown("---")
    st.subheader("Output Files")

    for file_path in output_files:
        if file_path.exists():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"{file_path.name}")
                st.caption(f"Size: {file_path.stat().st_size / 1024:.1f} KB")
            with col2:
                with open(file_path, 'rb') as f:
                    st.download_button(
                        label="Download",
                        data=f.read(),
                        file_name=file_path.name,
                        mime='text/csv',
                        key=f"download_{file_path.name}"
                    )

# Page configuration
st.set_page_config(
    page_title="Vanguard AI Assistant",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .assistant-message {
        background-color: #f5f5f5;
    }
    .tool-use {
        background-color: #fff3e0;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        color: #e65100;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    print("[INFO] Initialized new session")
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "output_files" not in st.session_state:
    st.session_state.output_files = []

# Sidebar
with st.sidebar:
    st.title("Configuration")

    st.markdown("---")

    st.subheader("Available Tools")
    tools_info = {
        "run_calculator": "Execute fund calculations",
        "query_weights": "Query historical weights",
        "list_calculations": "List calculation dates",
        "validate_weights": "Check UCITS compliance",
        "analyze_weight_trends": "Analyze weight trends"
    }

    for tool_name, description in tools_info.items():
        st.markdown(f"**{tool_name}**")
        st.caption(description)

    st.markdown("---")

    st.subheader("Agent Information")
    st.info(f"""
    **Provider**: {ACTIVE_PROVIDER.upper()}

    **Model**: {MODEL}

    **Max Tokens**: {MAX_TOKENS:,}

    **Tools Available**: {len(TOOLS)}
    """)

    st.markdown("---")

    # Clear conversation button
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.session_state.output_files = []
        st.rerun()

    st.markdown("---")

    st.subheader("Example Queries")
    examples = [
        "What can you help me with?",
        "Explain UCITS compliance",
        "List calculations for vanguard_lifestrat",
        "What tools do you have?"
    ]

    for example in examples:
        if st.button(example, key=f"example_{example[:20]}"):
            # Set a flag to process this example query
            st.session_state.pending_query = example
            st.rerun()

# Main area
st.title("Vanguard Fund Calculation AI Assistant")

# Display welcome message if no messages
if len(st.session_state.messages) == 0:
    st.info("""
    **Welcome!** I'm your AI assistant for the Vanguard fund calculation workflow.

    I can help you with:
    - Running fund calculations
    - Validating UCITS compliance
    - Querying historical data
    - Analyzing weight trends
    - Answering questions about the system

    **Try asking**: "What can you help me with?" or click an example in the sidebar.
    """)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            # Handle assistant messages with potential tool use indicators
            if "tool_calls" in message:
                for tool_call in message["tool_calls"]:
                    st.markdown(f'<div class="tool-use">[Tool] Using: {tool_call}</div>',
                              unsafe_allow_html=True)
            st.markdown(message["content"])

            # Display download buttons if this message has output files
            if "output_files" in message and message["output_files"]:
                display_download_section(message["output_files"])

# Check for pending query from example buttons
if "pending_query" in st.session_state and st.session_state.pending_query:
    prompt = st.session_state.pending_query
    st.session_state.pending_query = None  # Clear the flag
    print(f"[USER] Processing example query: {prompt}")
else:
    # Chat input
    prompt = st.chat_input("Ask me anything about fund calculations...")

if prompt:
    import time
    start_time = time.time()
    print(f"\n[USER] New message: {prompt[:100]}...")

    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare conversation history for API
    st.session_state.conversation_history.append({
        "role": "user",
        "content": prompt
    })

    # Keep only last 10 messages to prevent slowdown (5 exchanges)
    if len(st.session_state.conversation_history) > 10:
        st.session_state.conversation_history = st.session_state.conversation_history[-10:]
        print("[INFO] Trimmed conversation history to last 10 messages")

    # Get response from Claude
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        tool_placeholder = st.empty()
        status_placeholder = st.empty()

        try:
            # Initialize LLM client
            init_start = time.time()
            print(f"[API] Initializing {ACTIVE_PROVIDER.upper()} client...")
            status_placeholder.info(f"Connecting to {ACTIVE_PROVIDER.upper()}...")
            print(f"[TIMING] Client init: {(time.time() - init_start)*1000:.0f}ms")

            # Call LLM API
            api_start = time.time()
            print(f"[API] Calling {ACTIVE_PROVIDER.upper()} API (model: {MODEL})...")
            status_placeholder.info("Waiting for response...")

            if ACTIVE_PROVIDER == 'azure':
                # Azure OpenAI - Use simple function calling
                response = create_message(
                    messages=st.session_state.conversation_history,
                    tools=TOOLS,
                    system=SYSTEM_PROMPT
                )
            else:
                # Anthropic Claude - Full tool support
                response = create_message(
                    messages=st.session_state.conversation_history,
                    tools=TOOLS,
                    system=SYSTEM_PROMPT
                )

            print(f"[API] Response received")
            print(f"[TIMING] First API call: {(time.time() - api_start)*1000:.0f}ms")
            tool_calls = []
            iteration = 0

            # Handle tool use - works for both Anthropic and Azure
            if ACTIVE_PROVIDER == 'anthropic':
                stop_reason = response.stop_reason
                has_tool_calls = (stop_reason == "tool_use")
            else:  # azure
                # Check if Azure returned a function call
                message = response.choices[0].message
                has_tool_calls = hasattr(message, 'function_call') and message.function_call is not None
                stop_reason = 'function_call' if has_tool_calls else 'stop'

            while has_tool_calls:
                iteration += 1
                print(f"[TOOL] Processing tool use (iteration {iteration})...")

                # Execute tools based on provider
                tool_results = []

                if ACTIVE_PROVIDER == 'anthropic':
                    # Add assistant's response to history (Anthropic format)
                    st.session_state.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Process Anthropic tool calls
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_name = block.name
                            tool_calls.append(tool_name)

                            print(f"[TOOL] Executing: {tool_name} with input: {block.input}")

                            # Show tool usage
                            status_placeholder.info(f"Using tool: {tool_name}...")
                            tool_placeholder.markdown(
                                f'<div class="tool-use">[Tool] Using: {tool_name}</div>',
                                unsafe_allow_html=True
                            )

                            # Execute tool
                            tool_start = time.time()
                            result = execute_tool(tool_name, block.input)
                            print(f"[TIMING] Tool execution: {(time.time() - tool_start)*1000:.0f}ms")
                            print(f"[TOOL] Result type: {type(result)}")

                            # Extract output file paths if this is a calculator run
                            if tool_name == "run_calculator" and isinstance(result, str):
                                output_paths = extract_output_paths(result)
                                st.session_state.output_files.extend(output_paths)

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result
                            })

                    # Add tool results to history
                    st.session_state.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                else:  # azure
                    import json

                    # Get Azure function call
                    message = response.choices[0].message
                    function_call = message.function_call
                    tool_name = function_call.name
                    tool_calls.append(tool_name)

                    print(f"[TOOL] Executing: {tool_name} with arguments: {function_call.arguments}")

                    # Show tool usage
                    status_placeholder.info(f"Using tool: {tool_name}...")
                    tool_placeholder.markdown(
                        f'<div class="tool-use">[Tool] Using: {tool_name}</div>',
                        unsafe_allow_html=True
                    )

                    # Parse arguments
                    tool_input = json.loads(function_call.arguments)

                    # Add assistant's message with function call to history
                    st.session_state.conversation_history.append({
                        "role": "assistant",
                        "content": message.content or f"Calling {tool_name}..."
                    })

                    # Execute tool
                    tool_start = time.time()
                    result = execute_tool(tool_name, tool_input)
                    print(f"[TIMING] Tool execution: {(time.time() - tool_start)*1000:.0f}ms")
                    print(f"[TOOL] Result type: {type(result)}")

                    # Extract result text
                    if isinstance(result, dict) and 'content' in result:
                        result_content = result['content']
                        if isinstance(result_content, list) and len(result_content) > 0:
                            result_text = result_content[0].get('text', str(result))
                        else:
                            result_text = str(result)
                    else:
                        result_text = str(result)

                    # Extract output file paths if this is a calculator run
                    if tool_name == "run_calculator":
                        output_paths = extract_output_paths(result_text)
                        st.session_state.output_files.extend(output_paths)

                    # Add function result to history (OpenAI format)
                    st.session_state.conversation_history.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "content": result_text
                        }]
                    })

                # Get next response
                followup_start = time.time()
                print(f"[API] Getting follow-up response after tool use...")
                status_placeholder.info("Getting follow-up response...")
                response = create_message(
                    messages=st.session_state.conversation_history,
                    tools=TOOLS,
                    system=SYSTEM_PROMPT
                )
                print(f"[API] Follow-up response received")
                print(f"[TIMING] Follow-up API call: {(time.time() - followup_start)*1000:.0f}ms")

                # Check for more tool calls
                if ACTIVE_PROVIDER == 'anthropic':
                    stop_reason = response.stop_reason
                    has_tool_calls = (stop_reason == "tool_use")
                    print(f"[RESPONSE] Anthropic stop_reason: {stop_reason}")
                else:  # azure
                    message = response.choices[0].message
                    has_tool_calls = hasattr(message, 'function_call') and message.function_call is not None
                    stop_reason = 'function_call' if has_tool_calls else 'stop'
                    print(f"[RESPONSE] Azure has more function calls: {has_tool_calls}")

            # Clear status indicator
            status_placeholder.empty()

            # Extract final text response
            print("[RESPONSE] Extracting final text...")
            full_response = ""

            if ACTIVE_PROVIDER == 'azure':
                # Azure OpenAI response format
                full_response = response.choices[0].message.content
            else:
                # Anthropic Claude response format
                for block in response.content:
                    if hasattr(block, "text"):
                        full_response += block.text

            print(f"[RESPONSE] Final response length: {len(full_response)} characters")

            # Display final response
            message_placeholder.markdown(full_response)

            # Note: Download buttons will be displayed after rerun from message history

            # Add to conversation history
            if ACTIVE_PROVIDER == 'azure':
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": full_response
                })
            else:
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

            # Add to display messages
            assistant_message = {
                "role": "assistant",
                "content": full_response
            }
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            if st.session_state.output_files:
                assistant_message["output_files"] = st.session_state.output_files.copy()

            st.session_state.messages.append(assistant_message)
            total_time = time.time() - start_time
            print(f"[SUCCESS] Response completed successfully. Tool calls: {len(tool_calls)}")
            print(f"[TIMING] TOTAL TIME: {total_time*1000:.0f}ms ({total_time:.1f}s)\n")

            # Trigger rerun to re-render chat input
            st.rerun()

        except Exception as e:
            print(f"\n[ERROR] {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            print()

            st.error(f"Error: {type(e).__name__}")
            st.error(str(e))
            st.caption("Check the terminal console for detailed error information.")

            # Trigger rerun to re-render chat input even after error
            st.rerun()

# Footer
st.markdown("---")
st.caption(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"Messages: {len(st.session_state.messages)}")
