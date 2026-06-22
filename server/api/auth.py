from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from server.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from server.repositories.user import UserRepository
from server.api.auth_deps import get_current_user
from server.schemas.schemas import UserRegister, UserLogin, Token, TokenRefresh, UserOut, UserSettingsUpdate

router = APIRouter(prefix="/auth", tags=["Authentication"])
user_repository = UserRepository()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    existing = await user_repository.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    hashed = hash_password(user_data.password)
    user = await user_repository.create_user(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed
    )
    user["id"] = str(user["_id"])
    return user

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    user = await user_repository.get_user_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    user_id_str = str(user["_id"])
    access = create_access_token(data={"sub": user_id_str})
    refresh = create_refresh_token(data={"sub": user_id_str})
    
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh(token_refresh: TokenRefresh):
    payload = decode_token(token_refresh.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    user = await user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    access = create_access_token(data={"sub": user_id})
    refresh = create_refresh_token(data={"sub": user_id})
    
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout():
    # Stateless JWT logout is handled on client-side by deleting token.
    # Return success message.
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

@router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    settings_data = await user_repository.get_user_settings(current_user["id"])
    if not settings_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")
    
    # Serialize ObjectId
    settings_data["_id"] = str(settings_data["_id"])
    settings_data["user_id"] = str(settings_data["user_id"])
    return settings_data

@router.put("/settings")
async def update_settings(settings_data: UserSettingsUpdate, current_user: dict = Depends(get_current_user)):
    success = await user_repository.update_user_settings(
        user_id=current_user["id"],
        theme=settings_data.theme,
        model_preferences=settings_data.model_preferences
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update settings")
    return {"message": "Settings updated successfully"}
