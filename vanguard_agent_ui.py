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
from anthropic import Anthropic

# Import agent configuration and tools
try:
    from agent.config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, TOOLS, SYSTEM_PROMPT
    from agent.main import execute_tool
    print(f"[INFO] Agent modules loaded successfully. Model: {MODEL}, Tools: {len(TOOLS)}")
except Exception as e:
    print(f"[ERROR] Failed to import agent modules: {e}")
    raise

# Helper functions
def extract_output_paths(text: str) -> list:
    """Extract output file paths from tool result text."""
    paths = []
    # Pattern to match: "Output: path/to/file.csv"
    pattern = r'Output:\s*([^\n]+\.csv)'
    matches = re.findall(pattern, text)
    for match in matches:
        path = Path(match.strip())
        if path.exists():
            paths.append(path)
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
    **Model**: {MODEL.split('-')[-1].upper()}

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
st.caption("Powered by Claude Sonnet 4.5")

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
            # Initialize Anthropic client
            init_start = time.time()
            print("[API] Initializing Claude client...")
            status_placeholder.info("Connecting to Claude...")
            client = Anthropic(api_key=ANTHROPIC_API_KEY)
            print(f"[TIMING] Client init: {(time.time() - init_start)*1000:.0f}ms")

            # Call Claude API
            api_start = time.time()
            print(f"[API] Calling Claude API (model: {MODEL})...")
            status_placeholder.info("Waiting for response...")
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=st.session_state.conversation_history
            )

            print(f"[API] Response received. Stop reason: {response.stop_reason}")
            print(f"[TIMING] First API call: {(time.time() - api_start)*1000:.0f}ms")
            tool_calls = []
            iteration = 0

            # Handle tool use
            while response.stop_reason == "tool_use":
                iteration += 1
                print(f"[TOOL] Processing tool use (iteration {iteration})...")
                # Add assistant's response to history
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Execute tools
                tool_results = []
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

                # Get next response
                followup_start = time.time()
                print(f"[API] Getting follow-up response after tool use...")
                status_placeholder.info("Getting follow-up response...")
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=st.session_state.conversation_history
                )
                print(f"[API] Follow-up response received. Stop reason: {response.stop_reason}")
                print(f"[TIMING] Follow-up API call: {(time.time() - followup_start)*1000:.0f}ms")

            # Clear status indicator
            status_placeholder.empty()

            # Extract final text response
            print("[RESPONSE] Extracting final text...")
            full_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    full_response += block.text

            print(f"[RESPONSE] Final response length: {len(full_response)} characters")

            # Display final response
            message_placeholder.markdown(full_response)

            # Display download section for any output files
            if st.session_state.output_files:
                display_download_section(st.session_state.output_files)

            # Add to conversation history
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

            st.session_state.messages.append(assistant_message)
            total_time = time.time() - start_time
            print(f"[SUCCESS] Response completed successfully. Tool calls: {len(tool_calls)}")
            print(f"[TIMING] TOTAL TIME: {total_time*1000:.0f}ms ({total_time:.1f}s)\n")

        except Exception as e:
            print(f"\n[ERROR] {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            print()

            st.error(f"Error: {type(e).__name__}")
            st.error(str(e))
            st.caption("Check the terminal console for detailed error information.")

# Footer
st.markdown("---")
st.caption(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"Messages: {len(st.session_state.messages)}")
