"""
Vanguard Fund Calculation AI Assistant - DEBUG VERSION
"""

import streamlit as st
import os
import sys
from datetime import datetime

print("=" * 80)
print("DEBUG: Starting Streamlit application...")
print(f"DEBUG: Current working directory: {os.getcwd()}")
print(f"DEBUG: Python path: {sys.path}")
print("=" * 80)

# Try to import agent modules with detailed error reporting
try:
    print("DEBUG: Importing agent.config...")
    from agent.config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, TOOLS, SYSTEM_PROMPT
    print(f"DEBUG: Successfully imported config. Model: {MODEL}")
    print(f"DEBUG: API Key present: {'Yes' if ANTHROPIC_API_KEY else 'No'}")
    print(f"DEBUG: Number of tools: {len(TOOLS)}")
except Exception as e:
    print(f"ERROR importing agent.config: {e}")
    import traceback
    traceback.print_exc()
    st.error(f"Failed to import agent.config: {e}")
    st.stop()

try:
    print("DEBUG: Importing agent.main...")
    from agent.main import execute_tool
    print("DEBUG: Successfully imported agent.main")
except Exception as e:
    print(f"ERROR importing agent.main: {e}")
    import traceback
    traceback.print_exc()
    st.error(f"Failed to import agent.main: {e}")
    st.stop()

try:
    print("DEBUG: Importing Anthropic...")
    from anthropic import Anthropic
    print("DEBUG: Successfully imported Anthropic")
except Exception as e:
    print(f"ERROR importing Anthropic: {e}")
    import traceback
    traceback.print_exc()
    st.error(f"Failed to import anthropic library: {e}")
    st.stop()

print("DEBUG: All imports successful!")

# Page configuration
st.set_page_config(
    page_title="Vanguard AI Assistant (DEBUG)",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []

# Sidebar
with st.sidebar:
    st.title("DEBUG Configuration")

    st.info(f"""
    **Model**: {MODEL}
    **Max Tokens**: {MAX_TOKENS:,}
    **Tools Available**: {len(TOOLS)}
    **API Key**: {'✓ Set' if ANTHROPIC_API_KEY else '✗ Missing'}
    """)

    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.session_state.debug_logs = []
        print("DEBUG: Conversation cleared")
        st.rerun()

    st.markdown("---")
    st.subheader("Debug Logs")
    for log in st.session_state.debug_logs[-10:]:  # Show last 10 logs
        st.caption(log)

# Main area
st.title("Vanguard AI Assistant - DEBUG MODE")
st.warning("This is a debug version with verbose logging to the console")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    print("\n" + "=" * 80)
    print(f"DEBUG: New user message received: {prompt}")
    debug_log = f"{datetime.now().strftime('%H:%M:%S')} - User message received"
    st.session_state.debug_logs.append(debug_log)

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

    print(f"DEBUG: Conversation history length: {len(st.session_state.conversation_history)}")

    # Get response from Claude
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        status_placeholder = st.empty()

        try:
            print("DEBUG: Initializing Anthropic client...")
            status_placeholder.info("Connecting to Claude API...")

            # Initialize Anthropic client
            client = Anthropic(api_key=ANTHROPIC_API_KEY)
            print("DEBUG: Client initialized successfully")

            print("DEBUG: Sending request to Claude API...")
            status_placeholder.info("Waiting for Claude response...")

            # Call Claude API
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=st.session_state.conversation_history
            )

            print(f"DEBUG: Received response. Stop reason: {response.stop_reason}")
            print(f"DEBUG: Response content blocks: {len(response.content)}")

            tool_calls = []
            iteration = 0

            # Handle tool use
            while response.stop_reason == "tool_use":
                iteration += 1
                print(f"DEBUG: Tool use iteration {iteration}")
                status_placeholder.info(f"Processing tools (iteration {iteration})...")

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

                        print(f"DEBUG: Executing tool: {tool_name}")
                        print(f"DEBUG: Tool input: {block.input}")

                        status_placeholder.info(f"Using tool: {tool_name}")

                        # Execute tool
                        result = execute_tool(tool_name, block.input)
                        print(f"DEBUG: Tool result type: {type(result)}")
                        print(f"DEBUG: Tool result: {str(result)[:200]}...")

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

                print(f"DEBUG: Getting next response from Claude...")
                status_placeholder.info("Getting follow-up response...")

                # Get next response
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=st.session_state.conversation_history
                )

                print(f"DEBUG: Next response stop reason: {response.stop_reason}")

            status_placeholder.empty()  # Clear status

            # Extract final text response
            print("DEBUG: Extracting final text response...")
            full_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    full_response += block.text

            print(f"DEBUG: Final response length: {len(full_response)} characters")
            print(f"DEBUG: Final response preview: {full_response[:200]}...")

            # Display final response
            message_placeholder.markdown(full_response)

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

            debug_log = f"{datetime.now().strftime('%H:%M:%S')} - Response received successfully"
            st.session_state.debug_logs.append(debug_log)
            print("DEBUG: Response processing completed successfully!")

        except Exception as e:
            print("\n" + "!" * 80)
            print(f"ERROR: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            print("!" * 80 + "\n")

            error_msg = f"Error: {type(e).__name__}: {str(e)}"
            st.error(error_msg)
            st.error("Check the console/terminal for detailed error information")

            debug_log = f"{datetime.now().strftime('%H:%M:%S')} - ERROR: {str(e)}"
            st.session_state.debug_logs.append(debug_log)

# Footer
st.markdown("---")
st.caption(f"DEBUG MODE | Messages: {len(st.session_state.messages)} | "
          f"History: {len(st.session_state.conversation_history)}")

print("DEBUG: Page render complete")
