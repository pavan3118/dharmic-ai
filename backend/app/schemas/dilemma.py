from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class AnalysisMode(str, Enum):
    GITA = "gita"
    CHANAKYA = "chanakya"
    SYNTHESIS = "synthesis"

class DilemmaRequest(BaseModel):
    dilemma: str = Field(..., min_length=10, description="The user's real-life dilemma or question.")
    mode: AnalysisMode = Field(default=AnalysisMode.SYNTHESIS, description="Target perspective mode.")

class CitationItem(BaseModel):
    canonical_id: str
    tradition: str
    chapter: int
    verse_number: int
    sanskrit: str
    translation: str

class DilemmaResponse(BaseModel):
    mode: AnalysisMode
    analysis: str
    action_plan: List[str]
    citations: List[CitationItem]