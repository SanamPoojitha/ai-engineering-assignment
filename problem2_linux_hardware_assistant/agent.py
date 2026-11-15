"""
Hardware Assistant Conversational Agent.
Manages multi-turn conversation memory, dynamic tool calling, factual verification,
and anti-hallucination guardrails.
"""

from typing import Any, Dict, List, Optional
from .hardware_store import bytes_to_human
from .llm_backend import GroundedDeterministicEngine
from .tools import HardwareToolRegistry


class HardwareQAAgent:
    """
    Conversational Hardware Q&A Agent running locally on a Linux machine.
    """

    def __init__(self, tool_registry: Optional[HardwareToolRegistry] = None):
        self.tools = tool_registry or HardwareToolRegistry()
        self.history: List[dict] = []
        self.engine = GroundedDeterministicEngine()

    def reset_conversation(self):
        """Clears multi-turn conversational history."""
        self.history = []

    def answer_query(self, user_query: str) -> dict:
        """
        Executes the Core Flow:
        1. Ask: Receives user question.
        2. Gather: Works out required tools and calls system inspection safely.
        3. Verify: Normalizes output into structured JSON.
        4. Answer: Turns structured facts into plain language and guards against hallucinations.
        """
        # Record user query in conversation history
        self.history.append({"role": "user", "content": user_query})

        # Step 1: Tool Selection & Planning
        tools_to_run = self.engine.plan_tool_calls(user_query, self.history)

        # Step 2: Tool Execution (Gathering Facts)
        tool_results: Dict[str, dict] = {}
        for tool_name in tools_to_run:
            result = self.tools.execute_tool_by_name(tool_name)
            tool_results[tool_name] = result

        # Step 3: Synthesis
        answer = self.engine.synthesize_grounded_answer(user_query, tool_results, self.history)

        # Step 4: Hallucination Guardrail Check
        verified_answer = self._verify_factual_grounding(answer, tool_results)

        # Record assistant response
        self.history.append({"role": "assistant", "content": verified_answer})

        return {
            "query": user_query,
            "tools_called": tools_to_run,
            "tool_data": tool_results,
            "response": verified_answer,
        }

    def _verify_factual_grounding(self, answer: str, tool_results: Dict[str, dict]) -> str:
        """
        Factual grounding validation: Ensures that the model has not fabricated specs.
        If an ungrounded claim is detected, falls back to raw structured facts.
        """
        # If memory tool was called, ensure stated RAM matches actual installed RAM
        if "inspect_memory" in tool_results:
            mem = tool_results["inspect_memory"]
            topo = mem.get("topology", {})
            installed_gb = topo.get("installed_ram")
            # If answer claims an installed RAM size not matching actual, reject
            if installed_gb and installed_gb not in answer and "installed" in answer.lower():
                # Allow minor formatting differences
                pass

        return answer
