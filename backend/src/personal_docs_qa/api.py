import json

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Any, Iterator, Optional
from typing import Literal

from personal_docs_qa.config import get_allowed_frontend_origins
from personal_docs_qa.services.qa_service import answer_question, stream_answer_chunks


router = APIRouter()


def create_app() -> FastAPI:
    """Create the FastAPI app with environment-driven CORS settings."""
    fastapi_app = FastAPI(title="Personal Docs Q&A API")
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_frontend_origins(),
        allow_credentials=True,
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["*"],
    )
    fastapi_app.include_router(router)
    return fastapi_app

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question about local documents.")
    chat_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous user and assistant messages for follow-up questions.",
    )


class SourceItem(BaseModel):
    source: str
    chunk_index: Optional[int] = None
    preview: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


def format_sse_event(event: str, data: dict[str, Any]) -> str:
    """Convert a Python dictionary into one Server-Sent Events message."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "Personal Docs Q&A API is running. Use POST /ask or POST /ask/stream.",
    }


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        result = answer_question(
            request.question,
            chat_history=[message.model_dump() for message in request.chat_history],
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return AskResponse(**result)


@router.post("/ask/stream")
def ask_stream(request: AskRequest) -> StreamingResponse:
    try:
        sources, answer_stream = stream_answer_chunks(
            request.question,
            chat_history=[message.model_dump() for message in request.chat_history],
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    def event_generator() -> Iterator[str]:
        yield format_sse_event("sources", {"sources": sources})

        try:
            for chunk in answer_stream:
                chunk_text = str(getattr(chunk, "content", chunk))
                if not chunk_text:
                    continue

                yield format_sse_event("answer_chunk", {"content": chunk_text})
        except Exception as error:
            yield format_sse_event("error", {"message": str(error)})
            return

        yield format_sse_event("done", {"status": "completed"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


app = create_app()
