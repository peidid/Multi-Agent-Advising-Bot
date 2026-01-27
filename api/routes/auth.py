"""
Authentication endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import timedelta
from typing import Optional

from api.database import get_database
from api.models.user import User, UserCreate, UserLogin, Token, TokenData
from api.services.user_service import UserService
from api.services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES


router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> User:
    """
    Dependency to get the current authenticated user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = AuthService.decode_token(token)
    if token_data is None:
        raise credentials_exception

    if AuthService.is_token_expired(token_data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService(db)
    user = await user_service.get_user_by_id(token_data.user_id)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Optional[User]:
    """
    Dependency for optional authentication.
    """
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


def require_role(allowed_roles: list):
    """
    Dependency factory for role-based access control.
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not authorized for this action"
            )
        return user
    return role_checker


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Register a new user.
    """
    user_service = UserService(db)

    try:
        user = await user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    OAuth2 compatible token login.
    """
    user_service = UserService(db)
    user = await user_service.authenticate(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = AuthService.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Login with email and password (JSON body).
    """
    user_service = UserService(db)
    user = await user_service.authenticate(login_data.email, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = AuthService.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=User)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    Get current authenticated user's info.
    """
    return user


@router.post("/refresh", response_model=Token)
async def refresh_token(user: User = Depends(get_current_user)):
    """
    Refresh the access token.
    """
    access_token = AuthService.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
