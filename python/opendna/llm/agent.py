"""Agent framework for goal-based protein engineering tasks.

The agent takes a high-level goal in natural language (e.g. "design a stable
variant of ubiquitin"), decomposes it into steps using an LLM, executes each
step by calling tools, and reports back.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from opendna.llm.providers import chat
from opendna.llm.tools import TOOL_SCHEMAS, execute_tool

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert protein engineering assistant in OpenDNA, a free open-source platform for protein structure prediction, design, and analysis.

You have access to tools that can:
- Fold proteins (predict 3D structures from sequences via ESMFold)
- Score and analyze proteins (properties, Lipinski, hydropathy, disorder, etc.)
- Design alternative sequences (ESM-IF1 inverse folding)
- Run iterative optimization loops
- Apply mutations and predict their stability effects (ΔΔG)
- Import proteins from UniProt by name (ubiquitin, insulin, gfp, p53, kras, etc.)
- Detect antibody CDRs
- Predict pKa values, conservation scores, costs, and more

When a user asks you to do something, plan the steps and call tools one at a time. After each tool call, look at the result and decide what to do next. Be concise but informative.

If the user asks a general question without needing tools, just answer directly with your knowledge of protein science.

Always explain what you're doing in plain language so non-experts can follow along."""


@dataclass
class AgentStep:
    step_number: int
    thought: str
    tool_called: Optional[str]
    tool_arguments: Optional[dict]
    tool_result: Optional[dict]


@dataclass
class AgentRun:
    goal: str
    steps: list[AgentStep] = field(default_factory=list)
    final_answer: str = ""
    success: bool = False
    provider: str = ""


def run_agent(goal: str, max_steps: int = 8) -> AgentRun:
    """Run an agent to complete a goal.

    Iterates: ask LLM what to do next → execute tool → feed result back to LLM
    until the LLM produces a final answer or max_steps is reached.
    """
    run = AgentRun(goal=goal)
    messages: list[dict] = [
        {"role": "user", "content": goal},
    ]

    for step_num in range(1, max_steps + 1):
        try:
            response = chat(
                messages=messages,
                tools=TOOL_SCHEMAS,
                system=SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=800,
            )
            run.provider = response.provider
        except Exception as e:
            logger.warning(f"LLM call failed at step {step_num}: {e}")
            run.final_answer = f"LLM failed: {e}"
            return run

        # If no tool calls, this is the final answer
        if not response.tool_calls:
            run.final_answer = response.text or "(no response)"
            run.success = True
            return run

        # Execute each tool call (typically just one)
        for tc in response.tool_calls:
            tool_name = tc["name"]
            args = tc["arguments"]

            try:
                result = execute_tool(tool_name, args)
            except Exception as e:
                result = {"error": str(e)}

            run.steps.append(AgentStep(
                step_number=step_num,
                thought=response.text or "",
                tool_called=tool_name,
                tool_arguments=args,
                tool_result=result,
            ))

            # Add the tool call and result to message history for the next iteration
            messages.append({
                "role": "assistant",
                "content": response.text or f"Calling {tool_name}",
            })
            messages.append({
                "role": "user",
                "content": f"Tool {tool_name} returned: {json.dumps(result)[:1500]}",
            })

    run.final_answer = "Max steps reached without final answer."
    return run


def simple_chat(message: str, history: Optional[list[dict]] = None) -> dict:
    """Simple chat that uses tools when needed but isn't a multi-step agent."""
    messages = history or []
    messages.append({"role": "user", "content": message})

    response = chat(
        messages=messages,
        tools=TOOL_SCHEMAS,
        system=SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=600,
    )

    tool_results = []
    if response.tool_calls:
        for tc in response.tool_calls:
            try:
                result = execute_tool(tc["name"], tc["arguments"])
            except Exception as e:
                result = {"error": str(e)}
            tool_results.append({"tool": tc["name"], "result": result})

    return {
        "text": response.text,
        "provider": response.provider,
        "model": response.model,
        "tool_calls": response.tool_calls,
        "tool_results": tool_results,
    }
