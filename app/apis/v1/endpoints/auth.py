# backend/app/apis/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any

from app import crud, schemas, models
from app.database import get_db
from app.core.security import create_access_token, verify_password, verify_email_verification_token
from app.helper.email import send_verification_email

router = APIRouter()

@router.post("/register", response_model=schemas.User)
async def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Create new user and send email verification link.
    """
    db_user = crud.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = crud.create_user(db=db, user=user_in)
    await send_verification_email(user.email)
    return user


@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    elif not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified. Please check your inbox for the verification link.",
        )

    access_token = create_access_token(
        data={"sub": user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/verify-email", response_model=schemas.User)
def verify_email(token: str, db: Session = Depends(get_db)) -> Any:
    """
    Verify user's email address from the token sent to their email.
    """
    email = verify_email_verification_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired email verification token.",
        )
    
    user = crud.get_user_by_email(db, email=email)
    if not user:
        # This is an unlikely case if the token is valid
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.is_email_verified:
        return user # Or you could raise an HTTPException saying it's already verified

    user.is_email_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user
