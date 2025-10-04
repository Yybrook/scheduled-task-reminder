import os
import datetime
import typing
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.models import User, ScheduledTask
from app import auth
from app import ulity


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/ 的上一级目录
STATIC_DIR = os.path.join(BASE_DIR, "statics")


router = APIRouter()

class ScheduledTaskOut(BaseModel):
    id: int
    name: str
    message: typing.Optional[str] = None
    start_datetime: datetime.datetime
    repeat_type: str
    repeat_interval: int
    repeat_times: int
    advance_days: list[int] = list()
    current_task_datetime: datetime.datetime
    current_done_times: int
    current_advance_status: dict = dict()
    is_ended: bool

    # model_config = ConfigDict(from_attributes=True)  # 支持 ORM 对象直接序列化

    # 将数据库中存储的 JSON 字符串解析为列表或字典
    @field_validator("advance_days", mode="before")
    @classmethod
    def parse_advance_days(cls, v: str):
        if isinstance(v, str):
            try:
                return ulity.loads_advance_days(v)
            except:
                return list()
        return v

    @field_validator("current_advance_status", mode="before")
    @classmethod
    def parse_current_advance_status(cls, v: str):
        if isinstance(v, str):
            try:
                return ulity.loads_advance_status(v)
            except:
                return dict()
        return v


@router.get("/")
async def show_scheduled_tasks(request: Request):
    try:
        # 查看是否登录
        await auth.get_user_from_request(request)
        file_path = os.path.join(STATIC_DIR, "scheduled_tasks.html")
        return FileResponse(file_path, media_type="text/html")
    except:
        return RedirectResponse("/login")


@router.get("/search", response_model=list[ScheduledTaskOut])
async def list_scheduled_tasks(
    is_ended: typing.Optional[bool] = None,
    task_name: typing.Optional[str] = None,
    user: User = Depends(auth.get_user_from_request),
):
    query = ScheduledTask.filter(user_id=user.id)

    if task_name:
        query = query.filter(name__icontains=task_name)

    if is_ended is not None and is_ended != "":
        query = query.filter(is_ended=is_ended)

    results = await query.order_by("start_datetime")
    return results

@router.post("/{task_id}/ended")
async def mark_scheduled_task_ended(task_id: int, user: User = Depends(auth.get_user_from_request)):
    task = await ScheduledTask.get_or_none(id=task_id, user_id=user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"task[{task_id}] not found"
        )
    task.end(True)
    await task.save()
    return {"success": True, "message": "mark scheduled task ended successfully"}

