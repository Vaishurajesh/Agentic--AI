"""
Planning + content-generation logic for the autonomous agent.

The agent's autonomy shows up in two places:
1. plan_tasks()      -> the agent decides ITS OWN todo list for how to
                         fulfill the request (not a hardcoded pipeline).
2. classify_request() -> when the request is ambiguous or missing
                         information, the agent makes and records
                         reasonable assumptions instead of failing.

Every LLM-backed function has a matching offline fallback so the service
degrades gracefully to a deterministic template if no LLM key is present
or the LLM call fails (see llm_client.LLMUnavailableError).
"""
import logging
from .llm_client import LLMClient, LLMUnavailableError

log = logging.getLogger("agent.planner")

llm = LLMClient()

VALID_DOC_TYPES = [
    "proposal", "meeting_minutes", "project_plan", "business_report",
    "technical_design", "sop", "product_specification"
]


# --------------------------------------------------------------------------
# Step 1: Autonomous task planning
# --------------------------------------------------------------------------
def plan_tasks(user_request: str) -> list[dict]:
    """Ask the LLM to decompose the request into an ordered TODO list.
    Falls back to a generic-but-sensible plan if the LLM is unavailable.
    """
    system = (
        "You are the planning module of an autonomous document-writing agent. "
        "Given a user's request, break it down into a concise ordered list of "
        "execution steps the agent must take to produce a final Word document. "
        "Return ONLY a JSON object: {\"steps\": [\"step 1\", \"step 2\", ...]}. "
        "Keep it to 5-7 steps, concrete and specific to this request."
    )
    try:
        result = llm.chat_json(system, f"User request: {user_request}")
        steps = result.get("steps") or []
        if not steps:
            raise ValueError("empty steps")
        return [{"step": i + 1, "description": s, "status": "pending"} for i, s in enumerate(steps)]
    except (LLMUnavailableError, ValueError, KeyError) as e:
        log.warning("plan_tasks falling back to offline plan: %s", e)
        return _offline_plan()


def _offline_plan() -> list[dict]:
    steps = [
        "Interpret the request and identify the target document type",
        "Resolve missing or ambiguous details using reasonable assumptions",
        "Design a section outline appropriate for the document type",
        "Generate content for each section",
        "Run a self-check of the draft against the original request",
        "Revise content if the self-check finds gaps",
        "Render the final content into a formatted .docx file",
    ]
    return [{"step": i + 1, "description": s, "status": "pending"} for i, s in enumerate(steps)]


# --------------------------------------------------------------------------
# Step 2: Classification + assumption-making
# --------------------------------------------------------------------------
def classify_request(user_request: str) -> dict:
    """Determine document type, title, outline and any assumptions needed
    to fill gaps in an ambiguous request."""
    system = (
        "You are the analysis module of an autonomous document-writing agent. "
        f"Classify the user's request into exactly one of: {VALID_DOC_TYPES}. "
        "If the request is ambiguous, underspecified, or has conflicting "
        "requirements, DO NOT ask a clarifying question -- instead make the most "
        "reasonable professional assumption and record it explicitly. "
        "Return ONLY JSON of the form: "
        '{"document_type": "...", "title": "...", "assumptions": ["...","..."], '
        '"sections": ["Section A", "Section B", ...]} '
        "Choose 5-8 sections appropriate to the document type."
    )
    try:
        result = llm.chat_json(system, f"User request: {user_request}")
        if result.get("document_type") not in VALID_DOC_TYPES:
            result["document_type"] = "business_report"
        if not result.get("sections"):
            raise ValueError("no sections returned")
        return result
    except (LLMUnavailableError, ValueError, KeyError) as e:
        log.warning("classify_request falling back to offline classifier: %s", e)
        return _offline_classify(user_request)


def _offline_classify(user_request: str) -> dict:
    text = user_request.lower()
    if "meeting" in text or "minutes" in text:
        doc_type, sections = "meeting_minutes", [
            "Attendees", "Agenda", "Discussion Summary", "Decisions Made",
            "Action Items", "Next Meeting"
        ]
    elif "sop" in text or "procedure" in text or "standard operating" in text:
        doc_type, sections = "sop", [
            "Purpose", "Scope", "Roles & Responsibilities", "Procedure Steps",
            "Safety / Compliance Notes", "Revision History"
        ]
    elif "technical design" in text or "architecture" in text or "system design" in text:
        doc_type, sections = "technical_design", [
            "Overview", "Goals & Non-Goals", "Proposed Architecture",
            "Data Model", "API Design", "Risks & Mitigations", "Rollout Plan"
        ]
    elif "project plan" in text or "timeline" in text or "milestones" in text:
        doc_type, sections = "project_plan", [
            "Project Overview", "Objectives", "Scope", "Milestones & Timeline",
            "Resource Plan", "Risks", "Success Criteria"
        ]
    elif "spec" in text or "specification" in text or "product requirements" in text:
        doc_type, sections = "product_specification", [
            "Overview", "Problem Statement", "User Stories", "Functional Requirements",
            "Non-Functional Requirements", "Out of Scope", "Open Questions"
        ]
    elif "proposal" in text or "pitch" in text or "quote" in text:
        doc_type, sections = "proposal", [
            "Executive Summary", "Problem Statement", "Proposed Solution",
            "Scope of Work", "Timeline", "Pricing", "Next Steps"
        ]
    else:
        doc_type, sections = "business_report", [
            "Executive Summary", "Background", "Key Findings", "Analysis",
            "Recommendations", "Conclusion"
        ]

    assumptions = [
        "No LLM API key was configured (or the LLM call failed), so this "
        "document was produced using the agent's offline template fallback.",
        "Specific figures, names, and dates below are illustrative mock data "
        "since none were provided in the request.",
    ]
    title = user_request.strip().rstrip(".").capitalize()
    if len(title) > 80:
        title = title[:80] + "..."
    return {"document_type": doc_type, "title": title, "assumptions": assumptions, "sections": sections}


# --------------------------------------------------------------------------
# Step 3: Section content generation
# --------------------------------------------------------------------------
def generate_section_content(user_request: str, document_type: str, title: str, section_name: str) -> dict:
    """Generate the body content for a single section. Returns either
    {"body": "..."} or {"bullets": [...]} depending on what best fits."""
    system = (
        "You are the writing module of an autonomous document-writing agent. "
        f"Write the content for ONE section of a {document_type} titled '{title}'. "
        "Use mock/plausible data where specifics are not given. Be concrete and "
        "professional, 60-160 words. "
        'Return ONLY JSON: {"format": "paragraph"|"bullets", '
        '"body": "...", "bullets": ["...","..."]} '
        '(populate only the field matching "format").'
    )
    user = f"Original user request: {user_request}\nSection to write: {section_name}"
    try:
        result = llm.chat_json(system, user)
        return result
    except (LLMUnavailableError, ValueError, KeyError) as e:
        log.warning("generate_section_content falling back for '%s': %s", section_name, e)
        return {
            "format": "paragraph",
            "body": (
                f"[Auto-generated mock content for '{section_name}']. This section "
                f"would normally be populated by the LLM based on the request: "
                f"\"{user_request}\". Configure GROQ_API_KEY to enable live generation."
            ),
        }
