import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, Index
from backend.app.db.session import Base

class SourceTradition(str, enum.Enum):
    BHAGAVAD_GITA = "bhagavad_gita"
    CHANAKYA_NITI = "chanakya_niti"

class Verse(Base):
    __tablename__ = "verses"

    id = Column(Integer, primary_key=True, index=True)
    tradition = Column(Enum(SourceTradition), nullable=False, index=True)
    
    chapter = Column(Integer, nullable=False, index=True)
    verse_number = Column(Integer, nullable=False, index=True)
    canonical_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "BG_02_47", "CN_01_05"
    
    sanskrit_text = Column(Text, nullable=False)
    transliteration = Column(Text, nullable=True)
    english_translation = Column(Text, nullable=False)
    commentary_summary = Column(Text, nullable=True)
    
    edition = Column(String(100), default="Standard Verified Recension")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_tradition_chap_verse", "tradition", "chapter", "verse_number"),
    )