"""
The autonomous agent's orchestration loop.

Flow (mirrors a classic plan -> act -> reflect agent loop):

  1. PLAN     : plan_tasks()        -> agent's own TODO list
  2. UNDERSTAND: classify_request() -> doc type, title, sections, assumptions
  3. ACT      : generate_section_content() for each section (task execution)
  4. REFLECT  : self_check()        -> agent grades its own draft
  5. REVISE   : regenerate flagged sections (max 1 retry pass)
  6. DELIVER  : build_docx()        -> final artifact

Every step's status is tracked on the plan list and returned to the API
caller so the "agent-generated task list" is visible end-to-end, not just
implied.
"""
import os
import uuid
import logging

from . import planner, reflection, doc_builder

log = logging.getLogger("agent.orchestrator")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_agent(user_request: str) -> dict:
    # ---- 1. PLAN ----
    plan = planner.plan_tasks(user_request)

    def mark(step_idx, status):
        if 0 <= step_idx < len(plan):
            plan[step_idx]["status"] = status

    mark(0, "done")

    # ---- 2. UNDERSTAND / CLASSIFY ----
    classification = planner.classify_request(user_request)
    mark(1, "done")
    document_type = classification["document_type"]
    title = classification["title"]
    section_names = classification["sections"]
    assumptions = classification.get("assumptions", [])
    mark(2, "done")

    # ---- 3. ACT: generate each section ----
    sections = []
    for name in section_names:
        content = planner.generate_section_content(user_request, document_type, title, name)
        sections.append({
            "heading": name,
            "format": content.get("format", "paragraph"),
            "body": content.get("body", ""),
            "bullets": content.get("bullets", []),
        })
    mark(3, "done")

    # ---- 4. REFLECT ----
    check = reflection.self_check(user_request, document_type, sections)
    reflection_log = {"initial": check, "retried": False}

    # ---- 5. REVISE (bounded to one retry pass) ----
    if not check["passed"] and check.get("flagged_sections"):
        reflection_log["retried"] = True
        for i, sec in enumerate(sections):
            if sec["heading"] in check["flagged_sections"]:
                improved = planner.generate_section_content(
                    user_request + f"\n\nNOTE: previous draft of this section was flagged for: {check['issues']}",
                    document_type, title, sec["heading"],
                )
                sections[i] = {
                    "heading": sec["heading"],
                    "format": improved.get("format", "paragraph"),
                    "body": improved.get("body", ""),
                    "bullets": improved.get("bullets", []),
                }
        mark(4, "done")
        mark(5, "done")
    else:
        mark(4, "done")
        mark(5, "skipped (self-check passed)")

    # ---- 6. DELIVER ----
    filename = f"{uuid.uuid4().hex[:10]}_{document_type}.docx"
    output_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))
    doc_builder.build_docx(title, document_type, sections, assumptions, output_path)
    mark(6, "done")

    return {
        "request": user_request,
        "plan": plan,
        "document_type": document_type,
        "title": title,
        "assumptions": assumptions,
        "sections_generated": [s["heading"] for s in sections],
        "reflection": reflection_log,
        "file_name": filename,
        "download_url": f"/download/{filename}",
        "summary": (
            f"Generated a {document_type.replace('_', ' ')} titled '{title}' with "
            f"{len(sections)} sections. Self-check "
            f"{'passed on first draft' if check['passed'] else 'flagged issues and triggered a revision pass'}."
        ),
    }
