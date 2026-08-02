from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlmodel import Session, select
from app.db import get_session
from app.models import TokenStorage
from app.utils.crypto import encrypt_token

router = APIRouter()

class TokenCreate(BaseModel):
    platform: str
    token: str

class TokenOut(BaseModel):
    id: int
    platform: str

@router.post("/", response_model=TokenOut)
def create_token(payload: TokenCreate, session: Session = Depends(get_session)):
    enc = encrypt_token(payload.token)
    tok = TokenStorage(platform=payload.platform, encrypted_token=enc)
    session.add(tok)
    session.commit()
    session.refresh(tok)
    return TokenOut(id=tok.id, platform=tok.platform)

@router.get("/", response_model=List[TokenOut])
def list_tokens(session: Session = Depends(get_session)):
    res = session.exec(select(TokenStorage)).all()
    return [TokenOut(id=r.id, platform=r.platform) for r in res]

@router.delete("/{token_id}")
def delete_token(token_id: int, session: Session = Depends(get_session)):
    tok = session.get(TokenStorage, token_id)
    if not tok:
        raise HTTPException(status_code=404, detail="token not found")
    session.delete(tok)
    session.commit()
    return {"deleted": token_id}
