import os
from fastapi import HTTPException, APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from app.models.models import User
from app import auth


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/ 的上一级目录
STATIC_DIR = os.path.join(BASE_DIR, "statics")

router = APIRouter()


class UserIn(BaseModel):
    username: str
    password: str


@router.get("/")
async def login(request: Request):
    try:
        # 查看是否登录
        await auth.get_user_from_request(request)
        return RedirectResponse("/index")
    except:
        file_path = os.path.join(STATIC_DIR, "login.html")
        return FileResponse(file_path, media_type="text/html")

@router.post("/")
async def login(user_in: UserIn):
    user = await User.filter(username=user_in.username).first()
    if not user or not user.is_pwd_correct(user_in.password):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    response = JSONResponse({"message": "login success"})
    # 创建 session
    user_id_str = auth.create_session(user.id)
    # 将 user_id 加入 cookie
    response = auth.add_user_2_cookie(response, user_id_str)
    return response
