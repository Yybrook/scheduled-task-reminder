import datetime
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tortoise.contrib.fastapi import register_tortoise

from models.mysql_config import MYSQL_TORTOISE_ORM
from app.models.models import ScheduledTask
from routers import login, register, user, new_task, single_tasks, scheduled_tasks, index
import ulity, auth

_logger = logging.getLogger(__name__)

########################################################################
# 调度任务
########################################################################
# 定时器
scheduler = AsyncIOScheduler()

async def fresh_email_remind():
    """轮询所有任务，发送邮件提醒，一分钟执行一次"""
    try:
        _now = ulity.now()
        # 获取 task
        tasks = await ScheduledTask.all().prefetch_related("user")
        # 轮询
        for task in tasks:
            # 任务已经结束
            if task.is_ended:
                continue

            # 当前任务时间
            _task_dt = task.current_task_datetime
            if not _task_dt:
                continue

            # 获取提醒设置
            _adv_days = task.advance_days
            # 获取当前提醒状态
            _adv_status = task.current_advance_status
            for day in _adv_days:
                if day not in _adv_status:
                    _adv_status[day] = False
            # 正式提醒
            if _now >= _task_dt:
                context = {
                    "username": task.user.username,
                    "task_name": task.name,
                    "message": task.message,
                    "task_datetime": _task_dt.strftime("%Y-%m-%d %H:%M"),
                    "task_done": task.current_done_times + 1,
                    "repeat_type": task.repeat_type_str,
                    "note": "正式提醒"
                }
                await ulity.send_email_html(
                    email=task.user.email,
                    subject=f"[正式提醒] {task.name}",
                    context=context,
                    local_image_path="./statics/logo.jpg"
                )
                # 刷新下一次任务
                task.fresh_next_task()
            # 提前提醒
            else:
                delta = _task_dt - _now
                # 从小到大排列_adv_days
                # 时间间隔小于等于提醒时间 -> 提醒.跳出循环（实现只提醒一次）
                for day in _adv_days:
                    # 提醒
                    if delta <= datetime.timedelta(days=day) and not _adv_status[day]:
                        context = {
                            "username": task.user.username,
                            "task_name": task.name,
                            "message": task.message,
                            "task_datetime": _task_dt.strftime("%Y-%m-%d %H:%M"),
                            "task_done": task.current_done_times + 1,
                            "repeat_type": task.repeat_type_str,
                            "note": f"提前 {day} 天提醒"
                        }

                        await ulity.send_email_html(
                            email=task.user.email,
                            subject=f"[提前{day}天] {task.name}",
                            context=context,
                            local_image_path="./statics/logo.jpg"
                        )

                        _adv_status[day] = True
                        break

                task.set_current_advance_status(_adv_status)
            # 更新 task
            await task.save()
    except Exception as err:
        _logger.exception(f"fresh email reminder error: {err}")

async def fresh_single_tasks():
    """
    刷新single task, 写入数据库，每天执行
    :return:
    """
    try:
        # 获取 task
        tasks = await ScheduledTask.all().prefetch_related("user")
        # 轮询
        for task in tasks:
            # 任务已经结束
            if task.is_ended:
                continue
            # 生成任务实例
            await task.generate_single_tasks()
    except Exception as err:
        _logger.exception(f"fresh single tasks error: {err}")

def scheduler_do():
    # 每分钟执行
    scheduler.add_job(
        func=fresh_email_remind,
        trigger=IntervalTrigger(minutes=1),
        name="fresh_email_remind",
        misfire_grace_time=30,
        coalesce=True,
        max_instances=5,
        next_run_time=ulity.now(),
    )

    # 每天04:00:00执行
    scheduler.add_job(
        func=fresh_single_tasks,
        trigger=CronTrigger(hour=4, minute=0, second=0),
        name="fresh_single_tasks",
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1,
        next_run_time=ulity.now(),
    )

    scheduler.start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_do()
    yield
    # 关闭时执行
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

########################################################################
# Tortoise 初始化
########################################################################
register_tortoise(
    app,
    config=MYSQL_TORTOISE_ORM,
    # generate_schemas=True,  # 如果数据库为空，则自动生成对应表单，生产环境不要开
    # add_exception_handlers=True,  # 生产环境不要开，会泄露调试信息
)

########################################################################
# 加载静态文件
########################################################################
app.mount("/statics", StaticFiles(directory="statics", html=True), name="statics")

app.include_router(login.router, prefix="/login")
app.include_router(register.router, prefix="/register")
app.include_router(user.router, prefix="/user")
app.include_router(new_task.router, prefix="/new_task")
app.include_router(single_tasks.router, prefix="/single_tasks")
app.include_router(scheduled_tasks.router, prefix="/scheduled_tasks")
app.include_router(index.router, prefix="/index")

@app.get("/")
async def index(request: Request):
    return RedirectResponse("/index")

@app.post("/logout")
async def logout():
    response = JSONResponse({"message": "logout success"})
    response = auth.del_user_from_cookie(response)
    return response


