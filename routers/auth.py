from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_service import (
    DEFAULT_USERS,
    generate_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    username = req.username.strip()
    user = DEFAULT_USERS.get(username)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = generate_token(username)
    return {
        "token": token,
        "user": {
            "username": username,
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "avatar": user["avatar"],
        },
    }


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return user


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}
