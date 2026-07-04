"""HTTP layer: thin wrappers around service.py. No board rules live here.

Every mutation returns the full board JSON (the board is small and this keeps
the frontend a pure display layer) plus an `ETag: "<version>"` header.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import schemas, service
from .schemas import BoardData
from .seed import seed_board

router = APIRouter(prefix="/api")


def get_session() -> Session:  # overridden in main.create_app with a real session factory
    raise NotImplementedError


def board_response(session: Session) -> JSONResponse:
    # exclude_none drops absent archivedFrom/archivedAt, matching the frontend's
    # habit of deleting those keys on restore
    board = service.get_board(session)
    return JSONResponse(
        board.model_dump(exclude_none=True),
        headers={"ETag": f'"{service.get_version(session)}"'},
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- whole board -------------------------------------------------------------

@router.get("/board")
def read_board(session: Session = Depends(get_session)) -> JSONResponse:
    if not service.is_initialized(session):
        # First launch: seed the demo board so the UI never starts blank.
        # A board the user deliberately emptied stays empty (initialized flag).
        service.replace_board(session, seed_board())
    return board_response(session)


@router.put("/board")
def write_board(
    board: BoardData,
    session: Session = Depends(get_session),
    if_match: str | None = Header(default=None),
) -> JSONResponse:
    if if_match is not None:
        expected = if_match.strip().strip('"')
        current = str(service.get_version(session))
        if expected != current:
            raise HTTPException(
                status_code=412,
                detail=f"board version is {current}, If-Match said {expected}",
            )
    service.replace_board(session, board)
    return board_response(session)


# --- columns -------------------------------------------------------------------

@router.post("/columns")
def create_column(body: schemas.ColumnCreate, session: Session = Depends(get_session)) -> JSONResponse:
    service.add_column(session, body.title)
    return board_response(session)


@router.patch("/columns/{column_id}")
def patch_column(
    column_id: str, body: schemas.ColumnPatch, session: Session = Depends(get_session)
) -> JSONResponse:
    service.rename_column(session, column_id, body.title)
    return board_response(session)


@router.delete("/columns/{column_id}")
def remove_column(column_id: str, session: Session = Depends(get_session)) -> JSONResponse:
    service.delete_column(session, column_id)
    return board_response(session)


@router.post("/columns/{column_id}/archive-all")
def archive_all_cards(column_id: str, session: Session = Depends(get_session)) -> JSONResponse:
    service.archive_all(session, column_id)
    return board_response(session)


@router.post("/columns/{column_id}/cards")
def create_card(
    column_id: str, body: schemas.CardCreate, session: Session = Depends(get_session)
) -> JSONResponse:
    service.add_card(session, column_id, body.title, body.position)
    return board_response(session)


# --- cards -----------------------------------------------------------------------

@router.patch("/cards/{card_id}")
def patch_card(
    card_id: str, body: schemas.CardTextPatch, session: Session = Depends(get_session)
) -> JSONResponse:
    service.update_card_text(session, card_id, body.title, body.description)
    return board_response(session)


@router.post("/cards/{card_id}/move")
def move_card(
    card_id: str, body: schemas.CardMove, session: Session = Depends(get_session)
) -> JSONResponse:
    service.move_card(session, card_id, body.toColumnId, body.beforeCardId)
    return board_response(session)


@router.post("/cards/{card_id}/archive")
def archive_card(card_id: str, session: Session = Depends(get_session)) -> JSONResponse:
    service.archive_card(session, card_id)
    return board_response(session)


@router.post("/cards/{card_id}/restore")
def restore_card(card_id: str, session: Session = Depends(get_session)) -> JSONResponse:
    service.restore_card(session, card_id)
    return board_response(session)


@router.delete("/cards/{card_id}")
def remove_card(card_id: str, session: Session = Depends(get_session)) -> JSONResponse:
    service.delete_card(session, card_id)
    return board_response(session)


@router.put("/cards/{card_id}/labels/{label_id}")
def add_card_label(
    card_id: str, label_id: str, session: Session = Depends(get_session)
) -> JSONResponse:
    service.add_card_label(session, card_id, label_id)
    return board_response(session)


@router.delete("/cards/{card_id}/labels/{label_id}")
def remove_card_label(
    card_id: str, label_id: str, session: Session = Depends(get_session)
) -> JSONResponse:
    service.remove_card_label(session, card_id, label_id)
    return board_response(session)


@router.post("/cards/{card_id}/checklist")
def create_checklist_item(
    card_id: str, body: schemas.ChecklistCreate, session: Session = Depends(get_session)
) -> JSONResponse:
    service.add_checklist_item(session, card_id, body.text)
    return board_response(session)


@router.patch("/cards/{card_id}/checklist/{item_id}")
def patch_checklist_item(
    card_id: str,
    item_id: str,
    body: schemas.ChecklistPatch,
    session: Session = Depends(get_session),
) -> JSONResponse:
    service.update_checklist_item(session, card_id, item_id, body.done, body.text)
    return board_response(session)


@router.delete("/cards/{card_id}/checklist/{item_id}")
def remove_checklist_item(
    card_id: str, item_id: str, session: Session = Depends(get_session)
) -> JSONResponse:
    service.delete_checklist_item(session, card_id, item_id)
    return board_response(session)


# --- labels ------------------------------------------------------------------------

@router.post("/labels")
def create_label(body: schemas.LabelCreate, session: Session = Depends(get_session)) -> JSONResponse:
    service.add_label(session, body.name)
    return board_response(session)


@router.patch("/labels/{label_id}")
def patch_label(
    label_id: str, body: schemas.LabelPatch, session: Session = Depends(get_session)
) -> JSONResponse:
    service.update_label(session, label_id, body.name, body.bg, body.fg, body.dot)
    return board_response(session)


@router.delete("/labels/{label_id}")
def remove_label(label_id: str, session: Session = Depends(get_session)) -> JSONResponse:
    service.delete_label(session, label_id)
    return board_response(session)
