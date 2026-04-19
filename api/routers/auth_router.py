"""
Authentication router.

POST /api/auth/login  — accepts username + password, returns JWT.
"""

from fastapi import APIRouter, HTTPException, status

from api.auth import authenticate_single_user, create_access_token
from api.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    if not authenticate_single_user(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": body.username})
    return TokenResponse(access_token=token)
