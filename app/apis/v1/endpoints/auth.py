# backend/app/apis/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any

from app import crud, schemas, models
from app.database import get_db
from app.core.security import create_access_token, verify_password, verify_email_verification_token
from app.helper.email import send_verification_email, send_password_reset_email
from app.core.redis import is_email_resend_throttled
from app.core.security import create_password_reset_token, verify_password_reset_token, get_password_hash
from app.dependencies import get_current_user

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


@router.post("/login", response_model=schemas.LoginResponse)
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

    access_token = create_access_token(
        data={"sub": user.email}
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}


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
        return user  # Or you could raise an HTTPException saying it's already verified

    user.is_email_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/resend-verification-email")
async def resend_verification_email(
    request: schemas.ResendEmailRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Resend email verification link to a user.
    """
    if await is_email_resend_throttled(request.email):
        # Return a generic success message to prevent email enumeration
        return {"message": "If the email exists and is not verified, a new link will be sent shortly."}

    user = crud.get_user_by_email(db, email=request.email)
    if not user:
        # Return a generic success message to prevent email enumeration
        return {"message": "If the email exists and is not verified, a new link will be sent shortly."}

    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified.",
        )

    await send_verification_email(user.email)
    return {"message": "Verification email sent successfully."}


@router.post("/forgot-password")
async def forgot_password(
    request: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Request a password reset link for the given email.
    """
    # Always return a generic success message to prevent email enumeration
    user = crud.get_user_by_email(db, email=request.email)
    if user:
        await send_password_reset_email(user.email)

    return {"message": "If a user with that email exists, a password reset link will be sent."}


@router.post("/reset-password")
async def reset_password(
    request: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Reset user's password using a valid token.
    """
    email = verify_password_reset_token(request.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    user = crud.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.hashed_password = get_password_hash(request.new_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Password has been reset successfully."}


@router.post("/change-password")
async def change_password(
    request: schemas.ChangePasswordRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Change the password for the authenticated user.
    """
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password.",
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {"message": "Password changed successfully."}
