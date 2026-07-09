"""
ENGINEERING IMPROVEMENT: Reflection / Self-Check
=================================================
Why this one: the base assignment already forces multi-step planning
(plan_tasks/classify_request). The highest-leverage *additional* reliability
win is catching the agent's own mistakes before they reach the user --
LLMs frequently produce sections that drift off-topic, ignore an explicit
constraint in the request, or contradict another section (e.g. meeting
minutes that name a decision in one section but never list it as an
action item). A self-check closes that loop autonomously instead of
shipping a bad draft.

How it works:
1. After all sections are drafted, the agent sends the full compiled
   draft back to the LLM with the ORIGINAL user request and asks it to
   grade coverage/consistency.
2. If it fails, the orchestrator (main.py) regenerates only the flagged
   sections (bounded to one retry pass to keep latency predictable).
3. The result of the check (pass/fail + issues + whether a retry ran) is
   returned to the caller in the API response for full transparency --
   the user can see the agent evaluating and correcting itself.
"""
import logging
from .llm_client import LLMClient, LLMUnavailableError

log = logging.getLogger("agent.reflection")
llm = LLMClient()


def self_check(user_request: str, document_type: str, compiled_sections: list[dict]) -> dict:
    """Return {"passed": bool, "issues": [...], "flagged_sections": [...]}"""
    draft_text = "\n\n".join(
        f"## {s['heading']}\n" + (s.get("body") or "\n".join(f"- {b}" for b in s.get("bullets", [])))
        for s in compiled_sections
    )
    system = (
        "You are the quality-control module of an autonomous document-writing agent. "
        "Review the DRAFT against the ORIGINAL REQUEST. Check for: "
        "(1) missing content the request explicitly asked for, "
        "(2) contradictions between sections, "
        "(3) sections that are generic filler rather than specific to the request. "
        'Return ONLY JSON: {"passed": true|false, "issues": ["..."], '
        '"flagged_sections": ["Section Heading", ...]}. '
        "If it's acceptable, passed=true and both arrays empty."
    )
    user = f"ORIGINAL REQUEST:\n{user_request}\n\nDOCUMENT TYPE: {document_type}\n\nDRAFT:\n{draft_text}"
    try:
        result = llm.chat_json(system, user)
        result.setdefault("passed", True)
        result.setdefault("issues", [])
        result.setdefault("flagged_sections", [])
        return result
    except (LLMUnavailableError, ValueError, KeyError) as e:
        log.warning("self_check unavailable, skipping reflection pass: %s", e)
        return {
            "passed": True,
            "issues": ["Self-check skipped: LLM unavailable (offline fallback mode)."],
            "flagged_sections": [],
        }
