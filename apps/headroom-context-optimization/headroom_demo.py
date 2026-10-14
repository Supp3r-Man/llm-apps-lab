"""
Headroom Context Optimization Demo
==================================

This demo runs the real headroom.compress() on a "needle in a haystack" case
(100 log entries, one FATAL error) and reports the measured token savings.
No API key is needed: tokens are counted locally.

Run: python headroom_demo.py
"""

import json
import warnings
from datetime import datetime, timedelta

import headroom

warnings.filterwarnings("ignore")

MODEL = "gpt-4o"  # used only for token counting; no API call is made

# Generate 100 log entries with one critical error at position 67
def generate_test_logs():
    """Generate 100 log entries with a FATAL error buried at position 67."""
    services = ["api-gateway", "user-service", "inventory", "auth", "payment-gateway"]
    logs = []

    base_time = datetime(2024, 12, 15, 0, 0, 0)

    for i in range(100):
        if i == 67:
            # The critical error - the "needle"
            logs.append({
                "timestamp": (base_time + timedelta(hours=3, minutes=47, seconds=23)).isoformat() + "Z",
                "level": "FATAL",
                "service": "payment-gateway",
                "message": "Connection pool exhausted",
                "error_code": "PG-5523",
                "resolution": "Increase max_connections to 500 in config/database.yml",
                "affected_transactions": 1847
            })
        else:
            # Normal INFO logs - the "haystack"
            logs.append({
                "timestamp": (base_time + timedelta(hours=i//60, minutes=i%60)).isoformat() + "Z",
                "level": "INFO",
                "service": services[i % len(services)],
                "message": f"Request processed successfully - latency={50 + i}ms",
                "request_id": f"req-{i:06d}",
                "status_code": 200
            })

    return logs


NEEDLES = ["FATAL", "PG-5523", "Increase max_connections to 500", "1847"]


def build_messages(logs):
    """An OpenAI-format conversation where a tool returned all the logs."""
    return [
        {"role": "user", "content": "What caused the outage? Give the error code and the fix."},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "get_logs", "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": json.dumps(logs)},
    ]


def demo_without_headroom():
    """Baseline: the tool output goes to the model untouched."""
    logs = generate_test_logs()
    messages = build_messages(logs)

    print("=" * 60)
    print("BASELINE (Without Headroom)")
    print("=" * 60)
    print(f"Total log entries: {len(logs)}")
    print(f"Tool output characters: {len(messages[-1]['content']):,}")
    print()
    return messages


def demo_with_headroom(messages):
    """Run the real Headroom pipeline on the same conversation."""
    result = headroom.compress(messages, model=MODEL)
    tool_content = next(m["content"] for m in result.messages if m.get("role") == "tool")

    print("=" * 60)
    print("WITH HEADROOM (headroom.compress)")
    print("=" * 60)
    print(f"Tool output characters: {len(tool_content):,}")
    print(f"Tokens before: {result.tokens_before:,}")
    print(f"Tokens after:  {result.tokens_after:,}")
    print(f"Transforms applied: {', '.join(result.transforms_applied)}")
    print()
    print("Start of the compressed tool output:")
    for line in tool_content[:300].splitlines():
        print("  " + line)
    print()
    return result, tool_content


def calculate_savings(result, tool_content):
    """Report Headroom's measured savings and check the key facts survived."""
    saved_pct = result.tokens_saved / result.tokens_before * 100

    print("=" * 60)
    print("TOKEN SAVINGS (measured)")
    print("=" * 60)
    print(f"Tokens saved: {result.tokens_saved:,} of {result.tokens_before:,} ({saved_pct:.1f}%)")
    print()
    print("Are the facts needed to answer the question still present?")
    for needle in NEEDLES:
        print(f"  {'yes' if needle in tool_content else 'NO '}  {needle}")
    print()
    print("Savings depend on how repetitive the data is. This is one small,")
    print("very regular log sample, not a benchmark.")
    print()


def demo_langchain_integration():
    """Show LangChain integration example."""
    print()
    print("=" * 60)
    print("LANGCHAIN INTEGRATION")
    print("=" * 60)
    print("""
from langchain_openai import ChatOpenAI
from headroom.integrations import HeadroomChatModel

# Wrap your model - that's it!
llm = HeadroomChatModel(ChatOpenAI(model="gpt-4o"))

# Use exactly like before - compression is automatic
response = llm.invoke("Analyze these 100 logs and find the error")
""")


def demo_proxy_mode():
    """Show proxy mode example."""
    print("=" * 60)
    print("PROXY MODE (Zero Code Changes)")
    print("=" * 60)
    print("""
# Start the proxy
$ headroom proxy --port 8787

# Point Claude Code at it
$ ANTHROPIC_BASE_URL=http://localhost:8787 claude

# Point Cursor at it
$ OPENAI_BASE_URL=http://localhost:8787/v1 cursor

# Your existing code works unchanged - Headroom compresses transparently
""")


def main():
    print()
    print("  HEADROOM CONTEXT OPTIMIZATION DEMO")
    print("  ===================================")
    print("  Compress tool output before it reaches the model")
    print()

    # Run demos
    messages = demo_without_headroom()
    result, tool_content = demo_with_headroom(messages)
    calculate_savings(result, tool_content)
    demo_langchain_integration()
    demo_proxy_mode()

    print("=" * 60)
    print("GET STARTED")
    print("=" * 60)
    print("pip install headroom-ai[all]")
    print()
    print("GitHub: https://github.com/chopratejas/headroom")
    print("PyPI:   https://pypi.org/project/headroom-ai/")
    print("=" * 60)


if __name__ == "__main__":
    main()
