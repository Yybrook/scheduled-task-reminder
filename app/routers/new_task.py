import os
import typing
from fastapi import HTTPException, APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from app import auth
from app.models.models import User, ScheduledTask
from app import ulity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/ 的上一级目录
STATIC_DIR = os.path.join(BASE_DIR, "statics")


router = APIRouter()

class TaskIn(BaseModel):
    name: str
    message: str = ""
    start_date: str
    start_time: str
    repeat_type: str = "none"
    repeat_interval: int = -1
    repeat_times: int = -1
    advance_days: typing.List[int] = list()

@router.get("/")
async def create_new_task(request: Request):
    try:
        # 查看是否登录
        await auth.get_user_from_request(request)
        file_path = os.path.join(STATIC_DIR, "new_task.html")
        return FileResponse(file_path, media_type="text/html")
    except:
        return RedirectResponse("/login")

@router.post("/")
async def create_new_task(task_in: TaskIn, user: User = Depends(auth.get_user_from_request)):
    # 组合日期时间
    start_datetime = ulity.form_datetime(task_in.start_date, task_in.start_time)
    if not start_datetime:
        raise HTTPException(status_code=400, detail="日期时间格式错误")

    # 提前提醒天数
    advance_days_json = ulity.dumps_advance_days(task_in.advance_days)
    # 初始化当前提醒状态
    current_advance_status_json = ulity.init_advance_status(task_in.advance_days)

    # 创建序列任务
    task = await ScheduledTask.create(
        user=user,
        name=task_in.name,
        message=task_in.message,
        start_datetime=start_datetime,

        repeat_type=task_in.repeat_type,
        repeat_interval=task_in.repeat_interval,
        repeat_times=task_in.repeat_times,
        _advance_days=advance_days_json,

        current_task_datetime=start_datetime,
        _current_advance_status=current_advance_status_json,
    )

    # 生成单个任务实例
    await task.generate_single_tasks()

    return {"success": True, "message": "create new task successfully"}

