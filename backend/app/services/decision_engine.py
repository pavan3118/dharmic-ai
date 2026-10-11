import asyncio
import json
from typing import Any, AsyncGenerator, List

from backend.app.schemas.dilemma import AnalysisMode, DilemmaRequest, DilemmaResponse, CitationItem
from backend.app.services.retriever import retriever_service
from backend.app.services.gemini_service import gemini_service


def _to_int(value: Any, default: int = 0) -> int:
    """Chroma metadata may store numbers as strings; coerce safely."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_json(raw: str) -> dict:
    """Parse JSON from the model output, tolerating code fences or extra text."""
    text = (raw or "").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise ValueError("Model did not return valid JSON.")


class DecisionEngine:
    def _build_system_prompt(self, mode: AnalysisMode) -> str:
        base = (
            "You are the Dharmic AI Decision Engine, a citation-grounded guidance system.\n"
            "Rules:\n"
            "1. You MUST ground your analysis strictly in the provided verified context. Never invent verses or sutras.\n"
            "2. Distinguish clearly between source teachings and practical modern application.\n"
            "3. Return your final answer as pure JSON matching the schema below without markdown code fences."
        )
        if mode == AnalysisMode.GITA:
            lens = "Focus on duty (Dharma), emotional stability, selfless action (Karma Yoga), and detachment from outcomes."
        elif mode == AnalysisMode.CHANAKYA:
            lens = "Focus on practical strategy, risk mitigation, resource management, leverage, and disciplined execution."
        else:
            lens = "Synthesize inner clarity and detachment (Gita) with pragmatic execution, risk calculation, and strategy (Chanakya)."

        schema = (
            "JSON Format:\n"
            "{\n"
            '  "analysis": "In-depth reasoning addressing the user\'s dilemma...",\n'
            '  "action_plan": ["Action step 1", "Action step 2", "Action step 3"],\n'
            '  "referenced_canonical_ids": ["BG_02_47"]\n'
            "}"
        )
        return f"{base}\n\nMode Directive: {lens}\n\n{schema}"

    def _build_streaming_system_prompt(self, mode: AnalysisMode) -> str:
        base = (
            "You are the Dharmic AI Decision Engine, an authoritative, citation-grounded guidance counselor.\n"
            "Rules:\n"
            "1. Ground your advice strictly in the provided verified texts. Explicitly reference canonical IDs (e.g. [BG_02_47]).\n"
            "2. Structure your response into two distinct sections:\n"
            "   - **Philosophical & Strategic Analysis**\n"
            "   - **Prescribed Action Protocol** (numbered actionable steps)\n"
            "3. Output natural, beautifully formatted Markdown text. Do NOT wrap in JSON format."
        )
        if mode == AnalysisMode.GITA:
            lens = "Focus on duty (Dharma), inner poise, selfless execution (Karma Yoga), and freeing the mind from attachment to fruits."
        elif mode == AnalysisMode.CHANAKYA:
            lens = "Focus on realistic statecraft, pragmatic risk mitigation, strategic preservation of capital, and discretion."
        else:
            lens = "Harmonize internal detachment and righteous intent (Gita) with astute external strategy and contingency defense (Chanakya)."

        return f"{base}\n\nFramework Lens: {lens}"

    @staticmethod
    def _make_citation(canonical_id: str, meta: dict) -> CitationItem:
        return CitationItem(
            canonical_id=canonical_id,
            tradition=str(meta.get("tradition", "")),
            chapter=_to_int(meta.get("chapter", 0)),
            verse_number=_to_int(meta.get("verse_number", 0)),
            sanskrit=str(meta.get("sanskrit", "")),
            translation=str(meta.get("translation", "")),
        )

    def _prepare_context(self, request: DilemmaRequest):
        tradition_filter = None
        if request.mode == AnalysisMode.GITA:
            tradition_filter = "bhagavad_gita"
        elif request.mode == AnalysisMode.CHANAKYA:
            tradition_filter = "chanakya_niti"

        retrieved_sources = retriever_service.retrieve(
            query=request.dilemma,
            top_k=4,
            tradition=tradition_filter,
        )

        if not retrieved_sources:
            retrieved_sources = retriever_service.retrieve(
                query=request.dilemma,
                top_k=4,
                tradition=None,
            )

        if not retrieved_sources:
            raise ValueError(
                "No relevant source verses were found. Verify that the Chroma database contains records."
            )

        context_blocks = [f"[{src['id']}]\n{src['document']}" for src in retrieved_sources]
        context_str = "\n\n".join(context_blocks)

        prompt = (
            f"User Dilemma: {request.dilemma}\n\n"
            f"Verified Reference Context:\n{context_str}\n\n"
            f"Address the dilemma using only the teachings above."
        )

        valid_citations: List[CitationItem] = [
            self._make_citation(s["id"], s.get("metadata", {}) or {})
            for s in retrieved_sources
        ]

        return prompt, retrieved_sources, valid_citations

    def analyze(self, request: DilemmaRequest) -> DilemmaResponse:
        prompt, retrieved_sources, _ = self._prepare_context(request)
        system_instruction = self._build_system_prompt(request.mode)

        raw_response = gemini_service.generate_response(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.2,
        )

        data = _extract_json(raw_response)

        source_map = {s["id"]: (s.get("metadata", {}) or {}) for s in retrieved_sources}
        valid_citations: List[CitationItem] = [
            self._make_citation(c_id, source_map[c_id])
            for c_id in data.get("referenced_canonical_ids", [])
            if c_id in source_map
        ]

        return DilemmaResponse(
            mode=request.mode,
            analysis=data.get("analysis", ""),
            action_plan=data.get("action_plan", []),
            citations=valid_citations,
        )

    async def analyze_stream(self, request: DilemmaRequest) -> AsyncGenerator[str, None]:
        try:
            # Chroma retrieval is blocking, so run it off the event loop.
            prompt, _, valid_citations = await asyncio.to_thread(self._prepare_context, request)
            system_instruction = self._build_streaming_system_prompt(request.mode)

            # 1. Emit verified citation metadata immediately
            meta_payload = {
                "type": "meta",
                "mode": request.mode.value if hasattr(request.mode, "value") else str(request.mode),
                "citations": [c.model_dump() for c in valid_citations],
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"

            # 2. Stream generated tokens
            async for chunk in gemini_service.generate_stream(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.2,
            ):
                yield f"data: {json.dumps({'type': 'content', 'text': chunk})}\n\n"

            # 3. End-of-stream signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            # Once streaming has started FastAPI can't return an HTTP error,
            # so send the error to the frontend as an SSE event instead.
            print(f"[analyze_stream] ERROR: {e!r}")
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"


decision_engine = DecisionEngine()