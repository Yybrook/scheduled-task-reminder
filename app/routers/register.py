import os
from fastapi import HTTPException, APIRouter, Request
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from app.models.models import User
from app import ulity
from app import auth

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/ 的上一级目录
STATIC_DIR = os.path.join(BASE_DIR, "statics")


router = APIRouter()


class UserIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str


@router.get("/")
async def register(request: Request):
    file_path = os.path.join(STATIC_DIR, "register.html")
    response = FileResponse(file_path, media_type="text/html")
    # 删除 user
    response = auth.del_user_from_cookie(response)
    return response


@router.post("/", response_model=UserOut)
async def register(user_in: UserIn):
    # 检查用户名是否已存在
    if await User.filter(username=user_in.username).exists():
        raise HTTPException(status_code=400, detail="用户名已存在")

    hashed_pwd = ulity.get_hashed_pwd(user_in.password)

    user = await User.create(
        username=user_in.username,
        password_hash=hashed_pwd,
    )

    return UserOut(id=user.id, username=user.username)



