"""
Interactive CLI / REPL Interface for the Linux Hardware Assistant.
Provides a chat interface, multi-turn follow-ups, and a built-in demo walkthrough.
"""

import sys
import json
from .agent import HardwareQAAgent
from .tools import HardwareToolRegistry, MockLinuxBackend, NativeLinuxBackend


def print_banner():
    print("=" * 80)
    print(" PROBLEM 2: LINUX HARDWARE Q&A ASSISTANT (CLI INTERFACE)")
    print(" Safe System Inspection • Grounded Answers • Zero Arbitrary Shell Execution")
    print("=" * 80)
    print("Commands:")
    print("  • Type any hardware question (e.g., 'Can I add more RAM, and how much?')")
    print("  • Type '/demo' to run the interview prompt scenario walkthrough")
    print("  • Type '/history' to view conversation turns")
    print("  • Type '/clear' to reset chat memory")
    print("  • Type 'exit' or 'quit' to close")
    print("-" * 80)


def run_demo():
    """Runs the exact multi-turn conversational scenario from the interview prompt."""
    print("\n>>> RUNNING DEMO: Multi-Turn Conversational Hardware Q&A <<<\n")
    agent = HardwareQAAgent()

    queries = [
        "How much RAM do I have?",
        "Can I add more RAM, and how much?",
        "Is my SSD NVMe?",
        "and what about the GPU?",
    ]

    for q in queries:
        print(f"\nUser: {q}")
        res = agent.answer_query(q)
        print(f"[Tools Called]: {res['tools_called']}")
        print(f"Assistant: {res['response']}")
        print("-" * 60)

    print("\n>>> DEMO COMPLETE <<<\n")


def interactive_repl():
    print_banner()
    agent = HardwareQAAgent()

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting Hardware Assistant. Goodbye!")
                break
            elif user_input.lower() == "/demo":
                run_demo()
                continue
            elif user_input.lower() == "/clear":
                agent.reset_conversation()
                print("Conversation history cleared.")
                continue
            elif user_input.lower() == "/history":
                print(json.dumps(agent.history, indent=2))
                continue

            # Process query
            res = agent.answer_query(user_input)
            print(f"\n[Tools Called]: {res['tools_called']}")
            print(f"Assistant: {res['response']}")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo()
    else:
        interactive_repl()
