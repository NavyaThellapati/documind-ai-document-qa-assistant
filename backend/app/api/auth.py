from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limiter
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_token, validate_password_strength, verify_password
from app.models import RefreshToken, User
from app.schemas.auth import ForgotPasswordRequest, RefreshRequest, TokenResponse, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def issue_tokens(db: Session, user: User) -> TokenResponse:
    settings = get_settings()
    refresh_token = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id), refresh_token=refresh_token, user=user)


def as_aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    settings = get_settings()
    rate_limiter.check(request, "auth", settings.auth_rate_limit_per_minute)
    email = payload.email.lower()
    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return issue_tokens(db, user)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    settings = get_settings()
    rate_limiter.check(request, "auth", settings.auth_rate_limit_per_minute)
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    return issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    settings = get_settings()
    rate_limiter.check(request, "auth", settings.auth_rate_limit_per_minute)
    token = db.query(RefreshToken).filter(RefreshToken.token_hash == hash_token(payload.refresh_token)).first()
    now = datetime.now(timezone.utc)
    if not token or token.revoked_at or as_aware_utc(token.expires_at) < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")
    user = db.get(User, token.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    token.revoked_at = now
    return issue_tokens(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    token = db.query(RefreshToken).filter(RefreshToken.token_hash == hash_token(payload.refresh_token), RefreshToken.user_id == current_user.id).first()
    if token and not token.revoked_at:
        token.revoked_at = datetime.now(timezone.utc)
        db.commit()


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request):
    settings = get_settings()
    rate_limiter.check(request, "auth", settings.auth_rate_limit_per_minute)
    return {"message": "If an account exists for this email, password reset instructions will be sent."}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
