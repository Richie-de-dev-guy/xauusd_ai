"""
User profile router.

GET /api/user/me       — get current user info
POST /api/user/change-password — change user password
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_async_session
from api.auth import get_current_user, verify_password, hash_password
from api.models import User
from api.schemas import ChangePasswordRequest, UserResponse, UpdateTelegramRequest

router = APIRouter(prefix="/api/user", tags=["user"])


async def get_current_user_obj(
    username: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Get current user object from database."""
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user_obj),
) -> UserResponse:
    """Get current user profile info."""
    return UserResponse(
        username=current_user.username,
        telegram_chat_id=current_user.telegram_chat_id,
        created_at=current_user.created_at,
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_obj),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Change current user's password."""
    # Verify old password
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Old password is incorrect",
        )

    # Update password
    current_user.password_hash = hash_password(body.new_password)
    session.add(current_user)
    await session.commit()

    return {"message": "Password changed successfully"}


@router.patch("/telegram", status_code=status.HTTP_200_OK)
async def update_telegram(
    body: UpdateTelegramRequest,
    current_user: User = Depends(get_current_user_obj),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Update user's Telegram chat ID."""
    current_user.telegram_chat_id = body.telegram_chat_id
    session.add(current_user)
    await session.commit()

    return {"message": "Telegram chat ID updated successfully"}
