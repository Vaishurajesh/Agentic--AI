import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from agent.orchestrator import run_agent, OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("agent.api")

app = FastAPI(
    title="Autonomous Document Agent",
    description="Accepts a natural-language request, plans its own steps, "
                "generates content, self-checks the draft, and produces a .docx file.",
    version="1.0.0",
)


class AgentRequest(BaseModel):
    request: str = Field(..., min_length=3, max_length=4000)

    # --- Request validation & guardrail (basic input sanity check) ---
    @field_validator("request")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("request must not be blank")
        return v.strip()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/agent")
def agent_endpoint(payload: AgentRequest):
    try:
        result = run_agent(payload.request)
        return result
    except Exception as e:
        log.exception("Agent run failed")
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")


@app.get("/download/{filename}")
def download(filename: str):
    # guard against path traversal
    safe_name = os.path.basename(filename)
    path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe_name,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
