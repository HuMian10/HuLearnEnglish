"""Auth API router - registration, login, logout."""
from fastapi import APIRouter, Response, Request, HTTPException, Depends
from pydantic import BaseModel

from services.auth_service import register, authenticate, create_access_token, decode_token, get_user_by_id, update_email

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


async def get_current_user_id(request: Request) -> int:
    """Dependency: extract and verify user_id from JWT cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="登录已过期")
    return user_id


@router.post("/register")
async def api_register(req: RegisterRequest, response: Response, request: Request):
    if len(req.username) < 2 or len(req.username) > 20:
        return {"ok": False, "error": "用户名长度需要2-20个字符"}
    if len(req.password) < 4:
        return {"ok": False, "error": "密码至少4个字符"}

    result = await register(req.username, req.password, req.email)
    if not result["ok"]:
        return result

    token = create_access_token(result["user_id"])
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return {"ok": True, "user_id": result["user_id"], "username": req.username}


@router.post("/login")
async def api_login(req: LoginRequest, response: Response, request: Request):
    result = await authenticate(req.username, req.password)
    if not result["ok"]:
        return result

    token = create_access_token(result["user_id"])
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return {"ok": True, "user_id": result["user_id"], "username": req.username}


@router.post("/logout")
async def api_logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"ok": True}


@router.get("/me")
async def api_me(user_id: int = Depends(get_current_user_id)):
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {"ok": True, "user_id": user["id"], "username": user["username"], "email": user.get("email", ""), "created_at": user.get("created_at", "")}


class UpdateEmailRequest(BaseModel):
    email: str


@router.put("/email")
async def api_update_email(req: UpdateEmailRequest, user_id: int = Depends(get_current_user_id)):
    result = await update_email(user_id, req.email)
    return result
