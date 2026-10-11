from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.app.schemas.dilemma import DilemmaRequest, DilemmaResponse
from backend.app.services.decision_engine import decision_engine

app = FastAPI(
    title="Dharmic AI Decision Engine",
    version="1.0.0",
    description="Citation-grounded tactical and ethical counsel from the Bhagavad Gita and Chanakya Niti."
)

# Enable CORS for Next.js frontend running on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
def health_check():
    """System health validation endpoint."""
    return {
        "status": "healthy",
        "service": "dharmic-ai-backend",
        "engine": "active"
    }

@app.post("/api/v1/dilemmas/analyze", response_model=DilemmaResponse)
def analyze_dilemma(request: DilemmaRequest):
    """
    Standard blocking endpoint. Returns structured JSON containing
    philosophical analysis, action plan, and verified citations.
    """
    if len(request.dilemma.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Dilemma prompt must be at least 10 characters long."
        )
    try:
        return decision_engine.analyze(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/dilemmas/stream")
async def stream_dilemma(request: DilemmaRequest):
    """
    Server-Sent Events (SSE) streaming endpoint.
    Emits verified citation metadata immediately, then streams
    generated synthesis tokens progressively.
    """
    if len(request.dilemma.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Dilemma prompt must be at least 10 characters long."
        )
    try:
        return StreamingResponse(
            decision_engine.analyze_stream(request),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))