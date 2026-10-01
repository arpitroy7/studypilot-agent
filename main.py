import os
import sys
from typing import List, Optional, Union
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

# Import the existing StudyPilot agent reasoning and tools from run.py
from run import run_agentic_study_planner, parse_weak_topics, sanitize_error

app = FastAPI(
    title="StudyPilot Agent API",
    description="Agentic Study Planner REST API powered by Groq and tool calling.",
    version="1.0.0"
)

# Enable CORS for public consumption
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StudyPlanRequest(BaseModel):
    subject: str = Field(..., description="Subject name (e.g. Python, DBMS, Data Structures)")
    days: float = Field(..., gt=0, description="Available days until exam or milestone")
    hours_per_day: float = Field(..., gt=0, description="Daily available study hours")
    weak_topics: Optional[Union[List[str], str]] = Field(
        default=[],
        description="List or comma-separated string of weak topics"
    )


class StudyPlanResponse(BaseModel):
    status: str
    format: str
    response: str
    study_plan: str


@app.get("/")
def root():
    return {
        "name": "StudyPilot Agent API",
        "status": "online",
        "endpoint": "POST /api/agent"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/agent", response_model=StudyPlanResponse)
def generate_study_plan(payload: StudyPlanRequest):
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY environment variable is not configured on the server."
        )

    try:
        # Normalize weak topics (handles both list of strings or comma/newline separated string)
        weak_topics_list = parse_weak_topics(payload.weak_topics)

        # Run autonomous agent loop with genuine Groq tool calling
        study_plan = run_agentic_study_planner(
            subject=payload.subject,
            days=payload.days,
            hours_per_day=payload.hours_per_day,
            weak_topics=weak_topics_list,
            api_key=api_key
        )

        return StudyPlanResponse(
            status="success",
            format="markdown",
            response=study_plan,
            study_plan=study_plan
        )
    except Exception as err:
        safe_msg = sanitize_error(str(err), api_key)
        print(f"Agent error in /api/agent: {safe_msg}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Study plan generation failed: {safe_msg}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
