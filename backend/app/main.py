from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import AssessmentRequest, AssessmentResponse
from .services.assessment import create_assessment

app = FastAPI(
    title="RainAssess API",
    version="0.1.0",
    description="Preliminary residential rooftop rainwater harvesting assessment API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/assessment", response_model=AssessmentResponse)
async def assess(payload: AssessmentRequest) -> AssessmentResponse:
    return create_assessment(payload)
