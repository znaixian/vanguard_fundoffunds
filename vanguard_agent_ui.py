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
from anthropic import Anthropic

# Import agent configuration and tools
from agent.config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, TOOLS, SYSTEM_PROMPT
from agent.main import execute_tool

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
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

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
            st.session_state.messages.append({"role": "user", "content": example})
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

# Chat input
if prompt := st.chat_input("Ask me anything about fund calculations..."):
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

    # Get response from Claude
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        tool_placeholder = st.empty()

        try:
            # Initialize Anthropic client
            client = Anthropic(api_key=ANTHROPIC_API_KEY)

            # Call Claude API
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=st.session_state.conversation_history
            )

            tool_calls = []

            # Handle tool use
            while response.stop_reason == "tool_use":
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

                        # Show tool usage
                        tool_placeholder.markdown(
                            f'<div class="tool-use">[Tool] Using: {tool_name}</div>',
                            unsafe_allow_html=True
                        )

                        # Execute tool
                        result = execute_tool(tool_name, block.input)

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
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=st.session_state.conversation_history
                )

            # Extract final text response
            full_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    full_response += block.text

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

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.caption("Please check your API key and try again.")

# Footer
st.markdown("---")
st.caption(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"Messages: {len(st.session_state.messages)}")
