from __future__ import annotations

import logging
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import httpx
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.models import BrainstormSession
from app.schemas.brainstorm_generation import (
    GeneratedKeywordResult,
    KeywordGenerationResponse,
)
from app.schemas.research_keyword import ResearchKeywordCreate
from app.services.research_keyword import ResearchKeywordService
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError

logger = logging.getLogger(__name__)

# Minimal stopword list to avoid obvious filler keywords from heuristics
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "have",
    "will",
    "about",
    "there",
    "their",
    "would",
    "could",
    "should",
    "while",
    "where",
    "which",
    "whose",
    "your",
    "ours",
    "hers",
    "himself",
    "herself",
    "itself",
    "them",
    "they",
    "were",
    "been",
    "being",
    "also",
    "because",
    "between",
    "among",
    "using",
    "used",
    "over",
    "under",
    "after",
    "before",
    "again",
    "further",
    "then",
    "once",
    "here",
    "there",
    "why",
    "how",
    "what",
    "when",
    "who",
    "whom",
}


@dataclass
class LLMKeywordSuggestion:
    term: str
    rationale: Optional[str] = None
    weight: Optional[float] = None


class BrainstormLLMProvider:
    """Wrapper around the external LLM provider used for brainstorming."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        from app.core.config import settings

        # The config object may not define these attributes yet, hence getattr
        self.base_url = base_url or getattr(settings, "BRAINSTORM_AGENT_URL", None)
        self.api_key = api_key or getattr(settings, "BRAINSTORM_AGENT_API_KEY", None)
        self.model = model or getattr(settings, "BRAINSTORM_AGENT_MODEL", None)
        self.timeout = timeout

    async def generate_keywords(
        self,
        conversation: List[Dict[str, Any]],
        *,
        metadata: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[LLMKeywordSuggestion]:
        """Generate keyword suggestions from a conversation."""

        suggestions: List[LLMKeywordSuggestion] = []

        if self.base_url:
            try:
                suggestions = await self._call_external_provider(
                    conversation, metadata=metadata, limit=limit
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("LLM provider call failed: %s", exc, exc_info=True)

        if not suggestions:
            suggestions = self._heuristic_keywords(conversation, limit=limit)

        return suggestions

    async def _call_external_provider(
        self,
        conversation: List[Dict[str, Any]],
        *,
        metadata: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[LLMKeywordSuggestion]:
        """Call an HTTP-based provider for keyword generation."""

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {
            "conversation": conversation,
            "limit": limit,
        }
        if metadata:
            payload["metadata"] = metadata
        if self.model:
            payload["model"] = self.model

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        raw_items: Iterable[Any]
        if isinstance(data, dict):
            raw_items = data.get("keywords") or data.get("suggestions") or []
        elif isinstance(data, list):
            raw_items = data
        else:
            logger.debug("Unexpected response payload from LLM provider: %s", data)
            return []

        suggestions: List[LLMKeywordSuggestion] = []
        for item in raw_items:
            if isinstance(item, str):
                term = item.strip()
                rationale = None
                weight = None
            elif isinstance(item, dict):
                term = str(item.get("term", "")).strip()
                rationale = item.get("rationale")
                raw_weight = item.get("weight")
                try:
                    weight = float(raw_weight) if raw_weight is not None else None
                except (TypeError, ValueError):
                    weight = None
            else:
                continue

            if not term:
                continue

            suggestions.append(
                LLMKeywordSuggestion(term=term, rationale=rationale, weight=weight)
            )

        return suggestions

    def _heuristic_keywords(
        self, conversation: List[Dict[str, Any]], *, limit: int = 10
    ) -> List[LLMKeywordSuggestion]:
        """Fallback keyword extraction when no external provider is configured."""

        text_buffer: List[str] = []
        for message in conversation:
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    text_buffer.append(content)
                elif isinstance(content, list):
                    for segment in content:
                        if isinstance(segment, dict) and segment.get("type") == "text":
                            text = segment.get("text")
                            if isinstance(text, str):
                                text_buffer.append(text)
            elif isinstance(message, str):
                text_buffer.append(message)

        text = " ".join(text_buffer).lower()
        if not text:
            return []

        token_pattern = re.compile(r"[a-zA-Z][a-z0-9\-]{2,}")
        counts: Counter[str] = Counter()
        for token in token_pattern.findall(text):
            if token in _STOPWORDS:
                continue
            counts[token] += 1

        if not counts:
            return []

        max_count = max(counts.values())
        suggestions: List[LLMKeywordSuggestion] = []
        for term, count in counts.most_common(limit):
            weight = max(0.1, round(count / max_count, 2)) if max_count else None
            rationale = (
                f"Mentioned {count} times in the conversation"
                if count > 1
                else "Derived from the brainstorming conversation"
            )
            suggestions.append(
                LLMKeywordSuggestion(term=term, rationale=rationale, weight=weight)
            )

        return suggestions


class BrainstormGenerationService:
    """Service orchestrating keyword generation and persistence."""

    def __init__(
        self,
        db: Session,
        *,
        llm_provider: Optional[BrainstormLLMProvider] = None,
    ) -> None:
        self.db = db
        self.keyword_service = ResearchKeywordService(db)
        self.llm_provider = llm_provider or BrainstormLLMProvider()

    async def generate_keywords(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        limit: int = 10,
    ) -> KeywordGenerationResponse:
        """Generate keyword suggestions for a session and persist them."""

        session = await self._get_session_with_permissions(current_user_id, session_id)
        conversation = self._extract_conversation(session)
        if not conversation:
            raise ValidationError(
                "Brainstorm session does not have any conversation messages to analyse"
            )

        suggestions = await self.llm_provider.generate_keywords(
            conversation,
            metadata=session.session_data or {},
            limit=limit,
        )

        results: List[GeneratedKeywordResult] = []
        seen_terms: set[str] = set()

        for suggestion in suggestions:
            normalized_term = suggestion.term.strip().lower() if suggestion.term else ""
            if not normalized_term:
                results.append(
                    GeneratedKeywordResult(
                        term=suggestion.term or "",
                        rationale=suggestion.rationale,
                        weight=suggestion.weight,
                        status="skipped",
                        error="Suggestion is missing a keyword term",
                    )
                )
                continue

            if normalized_term in seen_terms:
                results.append(
                    GeneratedKeywordResult(
                        term=normalized_term,
                        rationale=suggestion.rationale,
                        weight=suggestion.weight,
                        status="skipped",
                        error="Duplicate suggestion from provider",
                    )
                )
                continue

            seen_terms.add(normalized_term)

            try:
                request = ResearchKeywordCreate(
                    term=suggestion.term,
                    weight=suggestion.weight,
                    source="ai",
                    rationale=suggestion.rationale,
                    is_primary=False,
                )
            except PydanticValidationError as exc:
                results.append(
                    GeneratedKeywordResult(
                        term=suggestion.term,
                        rationale=suggestion.rationale,
                        weight=suggestion.weight,
                        status="error",
                        error=f"Invalid suggestion payload: {exc.errors()}",
                    )
                )
                continue

            try:
                keyword_response, created = await self.keyword_service.create_keyword(
                    current_user_id,
                    session_id,
                    request,
                    upsert=True,
                )
            except (AuthorizationError, NotFoundError):
                # Propagate permission/not found errors so the API can surface them clearly
                raise
            except Exception as exc:  # pragma: no cover - unexpected persistence errors
                logger.exception("Failed to persist generated keyword '%s'", request.term)
                results.append(
                    GeneratedKeywordResult(
                        term=request.term,
                        rationale=suggestion.rationale,
                        weight=suggestion.weight,
                        status="error",
                        error=str(exc),
                    )
                )
                continue

            results.append(
                GeneratedKeywordResult(
                    term=keyword_response.term,
                    rationale=keyword_response.rationale,
                    weight=float(keyword_response.weight)
                    if keyword_response.weight is not None
                    else None,
                    status="created" if created else "updated",
                    keyword=keyword_response,
                    error=None,
                )
            )

        return KeywordGenerationResponse(session_id=session_id, suggestions=results)

    async def _get_session_with_permissions(
        self,
        current_user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> BrainstormSession:
        """Reuse keyword service helpers to ensure permissions are enforced."""

        # The keyword service already encapsulates the permission checks we need
        return await self.keyword_service._get_session_with_permissions(  # type: ignore[attr-defined]
            current_user_id,
            session_id,
            "create_brainstorm",
        )

    def _extract_conversation(self, session: BrainstormSession) -> List[Dict[str, Any]]:
        """Validate and normalize conversation data from the session."""

        session_data = session.session_data or {}
        conversation = session_data.get("conversation") if isinstance(session_data, dict) else None

        if conversation is None:
            return []

        if not isinstance(conversation, list):
            raise ValidationError("Conversation data must be stored as a list of messages")

        normalized: List[Dict[str, Any]] = []
        for index, message in enumerate(conversation):
            if isinstance(message, dict):
                if "content" not in message:
                    raise ValidationError(
                        f"Conversation message at index {index} is missing the 'content' field"
                    )
                normalized.append(message)
            elif isinstance(message, str):
                normalized.append({"role": "user", "content": message})
            else:
                raise ValidationError(
                    "Conversation messages must be dictionaries or strings"
                )

        return normalized


__all__ = [
    "BrainstormGenerationService",
    "BrainstormLLMProvider",
    "LLMKeywordSuggestion",
]

