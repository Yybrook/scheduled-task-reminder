import os
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, FileResponse
from app import auth


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/ 的上一级目录
STATIC_DIR = os.path.join(BASE_DIR, "statics")

router = APIRouter()


@router.get("/")
async def user(request: Request):
    try:
        # 查看是否登录
        await auth.get_user_from_request(request)
        file_path = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(file_path, media_type="text/html")
    except:
        return RedirectResponse("/login")

