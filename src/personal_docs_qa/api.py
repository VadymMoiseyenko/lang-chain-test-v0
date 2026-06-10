from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from personal_docs_qa.main import answer_question


app = FastAPI(title="Personal Docs Q&A API")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question about local documents.")


class SourceItem(BaseModel):
    source: str
    chunk_index: Optional[int] = None
    preview: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "Personal Docs Q&A API is running. Use POST /ask.",
    }


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        result = answer_question(request.question)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return AskResponse(**result)
