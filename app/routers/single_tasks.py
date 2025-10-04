import os
import datetime
import typing
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse, FileResponse
from app.models.models import User, SingleTask
from app import auth
from app import ulity


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/ 的上一级目录
STATIC_DIR = os.path.join(BASE_DIR, "statics")

router = APIRouter()

class ScheduledTaskOut(BaseModel):
    id: int
    name: str
    message: typing.Optional[str] = None

class SingleTaskOut(BaseModel):
    id : int
    task: ScheduledTaskOut
    datetime: datetime.datetime
    done_times: int
    repeat_times: int
    remark: typing.Optional[str] = None
    is_done: bool

    # model_config = ConfigDict(from_attributes=True)  # 支持 ORM 对象直接序列化

@router.get("/")
async def show_single_tasks(request: Request):
    try:
        # 查看是否登录
        await auth.get_user_from_request(request)
        file_path = os.path.join(STATIC_DIR, "single_tasks.html")
        return FileResponse(file_path, media_type="text/html")
    except:
        return RedirectResponse("/login")


@router.get("/search", response_model=list[SingleTaskOut])
async def list_single_tasks(
    start_date: str,
    end_date: str,
    is_done: typing.Optional[bool] = None,
    task_name: typing.Optional[str] = None,
    user: User = Depends(auth.get_user_from_request),
    days_ahead: int = 365
):
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)

    # 限制结束时间不超过今天+60天
    max_end = ulity.now(tz=None) + datetime.timedelta(days=days_ahead)
    if end_dt > max_end:
        end_dt = max_end

    query = SingleTask.filter(
        user_id=user.id,
        datetime__gte=start_dt,
        datetime__lt=end_dt         # 注意这里用 <，不包含end_dt
    ).prefetch_related("task")

    if is_done is not None and is_done != "":
        query = query.filter(is_done=is_done)

    if task_name:
        query = query.filter(task__name__icontains=task_name)

    results = await query.order_by("datetime")
    return results

@router.post("/{task_id}/done")
async def mark_single_task_done(task_id: int, user: User = Depends(auth.get_user_from_request)):
    task = await SingleTask.get_or_none(id=task_id, user_id=user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"task[{task_id}] not found",
        )
    task.done(True)
    await task.save()
    return {"success": True, "message": "mark single task done successfully"}
