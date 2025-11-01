"""
Main Entry Point for Vanguard AI Agent

Provides an interactive command-line interface using Anthropic's Claude API.
"""

import os
import sys
from anthropic import Anthropic
from .config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, TOOLS, SYSTEM_PROMPT

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Import tool implementations
from .tools.calculator_tools import run_calculator
from .tools.query_tools import query_weights, list_calculations
from .tools.validation_tools import validate_weights
from .tools.analysis_tools import analyze_weight_trends


def print_welcome():
    """Print welcome message and instructions."""
    print("=" * 70)
    print("Vanguard Fund Calculation AI Assistant")
    print("=" * 70)
    print()
    print("I can help you with:")
    print("  - Running fund calculations")
    print("  - Validating results and checking UCITS compliance")
    print("  - Querying historical data")
    print("  - Analyzing weight trends over time")
    print("  - Answering questions about the calculation system")
    print()
    print("Example queries:")
    print("  'Show me the latest calculations for vanguard_lifestrat'")
    print("  'What was the US Treasury weight last week?'")
    print("  'Validate yesterday's results'")
    print("  'Analyze LHMN21140 weight trend over the last month'")
    print()
    print("Type 'exit', 'quit', or 'bye' to end the session")
    print("=" * 70)
    print()


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    Execute a tool based on its name and input.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Input parameters for the tool

    Returns:
        Tool execution result as string
    """
    try:
        # Map tool names to functions
        tool_map = {
            "run_calculator": run_calculator,
            "query_weights": query_weights,
            "list_calculations": list_calculations,
            "validate_weights": validate_weights,
            "analyze_weight_trends": analyze_weight_trends
        }

        if tool_name not in tool_map:
            return f"Error: Unknown tool '{tool_name}'"

        # Execute the tool (Note: tools are now synchronous, not async)
        result = tool_map[tool_name](tool_input)

        # Extract text from result
        if isinstance(result, dict):
            if "is_error" in result and result["is_error"]:
                return f"Error: {result['content'][0]['text']}"
            return result["content"][0]["text"]

        return str(result)

    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


def interactive_session():
    """Run an interactive session with the Vanguard AI agent."""
    print_welcome()

    # Initialize Anthropic client
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Conversation history
    messages = []

    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\nGoodbye! Have a great day.")
                break

            # Add user message to history
            messages.append({
                "role": "user",
                "content": user_input
            })

            # Call Claude
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            # Process response
            print("\nAssistant: ", end="", flush=True)

            # Handle tool use
            while response.stop_reason == "tool_use":
                # Add assistant's response to messages
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Execute tools
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"[Using tool: {block.name}]", flush=True)

                        # Execute tool
                        result = execute_tool(block.name, block.input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                # Add tool results to messages
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # Get next response from Claude
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages
                )

            # Display final response
            for block in response.content:
                if hasattr(block, "text"):
                    print(block.text, flush=True)

            # Add final assistant response to history
            messages.append({
                "role": "assistant",
                "content": response.content
            })

        except KeyboardInterrupt:
            print("\n\nSession interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("You can continue or type 'exit' to quit.")
            # Don't add failed exchanges to history


def main():
    """Main entry point."""
    try:
        interactive_session()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\nFatal error: {e}")
        print("Please check your configuration and try again.")


if __name__ == "__main__":
    main()
