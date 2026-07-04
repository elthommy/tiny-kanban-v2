from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import service
from .schemas import BoardData
from .seed import seed_board

router = APIRouter(prefix="/api")


def get_session() -> Session:  # overridden in main.create_app with a real session factory
    raise NotImplementedError


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/board")
def read_board(session: Session = Depends(get_session)) -> JSONResponse:
    if service.is_initialized(session):
        board = service.get_board(session)
    else:
        # First launch: seed the demo board so the UI never starts blank.
        # A board the user deliberately emptied stays empty (initialized flag).
        board = seed_board()
        service.replace_board(session, board)
    # exclude_none drops absent archivedFrom/archivedAt, matching the frontend's
    # habit of deleting those keys on restore
    return JSONResponse(board.model_dump(exclude_none=True))


@router.put("/board")
def write_board(board: BoardData, session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        service.replace_board(session, board)
    except service.BoardValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok"}
