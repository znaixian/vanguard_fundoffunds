# Streamlit UI for Vanguard AI Agent

Beautiful web interface for the Vanguard fund calculation AI assistant.

## Features

- **ChatGPT-style interface** with conversation bubbles
- **Sidebar with tools list** and configuration
- **Example queries** for quick start
- **Tool usage indicators** showing when tools are being called
- **Conversation history** maintained throughout session
- **Clean, professional design** without emojis (Windows compatible)

## How to Start

### Method 1: Direct Command

```bash
cd vanguard-fundoffunds
streamlit run vanguard_agent_ui.py
```

### Method 2: Via Python Module

```bash
cd vanguard-fundoffunds
python -m streamlit run vanguard_agent_ui.py
```

## What You'll See

The interface will open in your default web browser at:

```
http://localhost:8501
```

## Interface Layout

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  [Sidebar]              [Main Chat Area]           │
│  - Configuration        - Welcome message           │
│  - Tools List           - Chat bubbles              │
│  - Agent Info           - User messages (blue)      │
│  - Clear Button         - Assistant messages (gray) │
│  - Example Queries      - Chat input at bottom     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Features in Detail

### Sidebar

**Configuration Section**
- Shows 5 available tools with descriptions

**Agent Information**
- Model being used (Sonnet 4.5)
- Max tokens setting
- Number of tools available

**Clear Conversation**
- Button to reset the chat and start fresh

**Example Queries**
- Click-to-send example questions
- Great for first-time users

### Main Area

**Chat Interface**
- Messages appear in conversation format
- User messages on the left (blue background)
- Assistant responses on the right (gray background)
- Tool usage shown in orange boxes: `[Tool] Using: tool_name`

**Input Box**
- Type your question at the bottom
- Press Enter to send
- Natural language supported

### Tool Usage Display

When the agent uses a tool, you'll see:

```
[Tool] Using: list_calculations
```

This shows you what's happening behind the scenes.

## Example Session

1. **Start the UI**: `streamlit run vanguard_agent_ui.py`
2. **Browser opens** automatically to localhost:8501
3. **See welcome message** with capabilities
4. **Type a question**: "What can you help me with?"
5. **Get response** from Claude
6. **Continue conversation** - history is maintained
7. **Click "Clear Conversation"** when you want to start fresh

## Advantages Over Command Line

- **Visual appeal**: Modern, clean interface
- **Easier to read**: Formatted chat bubbles
- **More intuitive**: Click examples, clear conversations
- **Better UX**: Scroll through history, copy/paste easily
- **Professional**: Share with team members
- **Markdown support**: Code blocks, tables, formatting

## Tips

- **Use example queries** in sidebar to get started
- **Clear conversation** before starting a new topic
- **Tool indicators** show when data is being fetched
- **Session persists** as long as the browser tab is open
- **Refresh page** to restart completely

## Troubleshooting

### Port Already in Use

If you see "Address already in use":

```bash
streamlit run vanguard_agent_ui.py --server.port 8502
```

### Can't Find streamlit Command

Make sure it's installed:

```bash
pip install streamlit>=1.28.0
```

Or use full path:

```bash
python -m streamlit run vanguard_agent_ui.py
```

### Browser Doesn't Open

Manually navigate to: `http://localhost:8501`

## Keyboard Shortcuts

- **Ctrl+Enter**: Send message
- **Ctrl+K**: Focus on input
- **Ctrl+R**: Refresh page (restart session)

## Cost Monitoring

Each message uses the same API as the command-line version:
- Simple questions: ~$0.01-$0.02
- Tool usage: ~$0.02-$0.05
- Long conversations: ~$0.05-$0.15

Monitor at: https://console.anthropic.com

---

**Ready to use!** Just run `streamlit run vanguard_agent_ui.py` and start chatting.
