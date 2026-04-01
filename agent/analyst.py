"""
AI Agent — uses OpenAI GPT-4o with function calling to analyze shrinkflation data.
Implements a full agentic loop: send message -> execute tools -> return results -> repeat.
"""

import json
from datetime import datetime, timezone

from openai import OpenAI

from config.settings import OPENAI_API_KEY, AGENT_MODEL
from agent.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
from db.models import AgentInsight, get_session

SYSTEM_PROMPT = """You are a data analyst specializing in consumer price transparency. \
You have access to a live database tracking shrinkflation across thousands of grocery products. \
Your job is to analyze trends, surface surprising insights, and explain findings clearly to \
consumers and journalists. Always cite specific numbers. Be direct and data-driven.

When presenting data:
- Format currencies as $X.XX
- Format percentages as +X.X%
- Use markdown for structure
- Lead with the most surprising finding
- Keep responses concise but substantive"""


def _get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set. Add it to your .env file.")
    return OpenAI(api_key=OPENAI_API_KEY)


def _run_agent_loop(client: OpenAI, messages: list[dict]) -> str:
    """
    Full agentic loop:
    1. Send messages to GPT-4o
    2. If response has tool_calls, execute them
    3. Send results back
    4. Repeat until final text response
    """
    while True:
        response = client.chat.completions.create(
            model=AGENT_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # Check if we need to execute tools
        if not message.tool_calls:
            return message.content or ""

        # Add assistant message with tool calls to conversation
        messages.append(message)

        # Execute each tool and send results back
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}

            if tool_name in TOOL_FUNCTIONS:
                result = TOOL_FUNCTIONS[tool_name](**tool_args)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str),
            })


def _run_agent_loop_streaming(client: OpenAI, messages: list[dict]):
    """
    Streaming agentic loop — yields text chunks for real-time display.
    Handles tool calls internally, only streams the final text response.
    """
    while True:
        # First, non-streaming call to check for tool use
        response = client.chat.completions.create(
            model=AGENT_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        if not message.tool_calls:
            # Final response — now stream it
            stream = client.chat.completions.create(
                model=AGENT_MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
            return

        # Execute tools
        messages.append(message)
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}

            if tool_name in TOOL_FUNCTIONS:
                result = TOOL_FUNCTIONS[tool_name](**tool_args)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str),
            })


def chat_with_data(user_question: str) -> str:
    """User asks a question, agent pulls relevant tools and answers."""
    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_question},
    ]
    return _run_agent_loop(client, messages)


def chat_with_data_streaming(user_question: str):
    """Streaming version of chat_with_data — yields text chunks."""
    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_question},
    ]
    yield from _run_agent_loop_streaming(client, messages)


def generate_daily_insight() -> str:
    """Agent autonomously analyzes data and writes one key insight."""
    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Analyze the latest shrinkflation data and write ONE key insight "
                "that would surprise consumers. Use the tools to pull current stats, "
                "look at recent flags, and identify the most interesting trend. "
                "Keep it to 2-3 sentences, punchy and data-driven. "
                "Start with the most surprising number."
            ),
        },
    ]

    insight = _run_agent_loop(client, messages)

    # Store in DB
    try:
        session = get_session()
        record = AgentInsight(
            insight_type="daily",
            content=insight,
        )
        session.add(record)
        session.commit()
        session.close()
    except Exception:
        pass

    return insight


def generate_weekly_report() -> str:
    """Agent compiles a full markdown weekly report."""
    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Generate a comprehensive weekly shrinkflation report. Use all available "
                "tools to gather data. Structure the report as:\n\n"
                "1. **Executive Summary** (3 sentences)\n"
                "2. **Top 5 Worst Offenders This Week** (brand, product count, avg increase)\n"
                "3. **Most Surprising Finding** (something unexpected in the data)\n"
                "4. **Fastest Growing Category** (which category's shrinkflation rate is rising)\n"
                "5. **Consumer Advice** (actionable tips based on the data)\n\n"
                "Use specific numbers throughout. Format as clean markdown."
            ),
        },
    ]

    report = _run_agent_loop(client, messages)

    # Store in DB
    try:
        session = get_session()
        record = AgentInsight(
            insight_type="weekly",
            content=report,
        )
        session.add(record)
        session.commit()
        session.close()
    except Exception:
        pass

    return report
