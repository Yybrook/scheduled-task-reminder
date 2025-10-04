import os
import typing
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel, EmailStr
from app.models.models import User
from app import auth, ulity


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/ 的上一级目录
STATIC_DIR = os.path.join(BASE_DIR, "statics")


router = APIRouter()

class ProfileIn(BaseModel):
    email: typing.Optional[EmailStr] = None   # 校验邮箱格式，可选字段

class ProfileOut(BaseModel):
    id: int
    username: str
    email: typing.Optional[str] = None


@router.get("/")
async def show_user(request: Request):
    try:
        # 查看是否登录
        await auth.get_user_from_request(request)
        file_path = os.path.join(STATIC_DIR, "user.html")
        return FileResponse(file_path, media_type="text/html")
    except:
        return RedirectResponse("/login")


@router.get("/me", response_model=ProfileOut)
async def get_current_user_info(user: User = Depends(auth.get_user_from_request)):
    return ProfileOut(
        id=user.id,
        username=user.username,
        email=user.email
    )


@router.get("/profile", response_model=ProfileOut)
async def get_profile(user: User = Depends(auth.get_user_from_request)):
    return ProfileOut(
        id=user.id,
        username=user.username,
        email=user.email
    )

@router.post("/profile")
async def update_profile(profile: ProfileIn, user: User = Depends(auth.get_user_from_request)):
    user.email = profile.email
    await user.save()
    return {"success": True, "message": "profile update successfully"}


@router.post("/email")
async def test_email(profile: ProfileIn, user: User = Depends(auth.get_user_from_request)):
    context = {
        "username": user.username,
        "task_name": "邮件测试任务",
        "message": "用于电子邮件的发送测试，无需回复",
        "task_datetime": ulity.now().strftime("%Y-%m-%d %H:%M"),
        "task_done": 1,
        "repeat_type": "不重复",
        "note": "邮件测试"
    }
    try:
        await ulity.send_email_html(
            email=profile.email,
            subject=f"[邮件测试] 邮件测试任务",
            context=context,
            local_image_path="./statics/logo.jpg"
        )
        return {"success": True, "message": "send mail successfully" }
    except Exception as err:
        return {"success": False, "error": str(err) }
