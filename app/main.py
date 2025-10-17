from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from models.mysql_config import MYSQL_TORTOISE_ORM
from routers import login, register, user, new_task, single_tasks, scheduled_tasks, index, mail
import ulity, auth
from app.worker.mail_sender import MailSender
from app.worker import fresher

# 定时器
scheduler = AsyncIOScheduler()

def scheduler_do(app: FastAPI):
    # 每分钟执行
    scheduler.add_job(
        func=fresher.fresh_email_remind,
        kwargs={"app": app},
        trigger=IntervalTrigger(minutes=1),
        name="fresh_email_remind",
        misfire_grace_time=30,
        coalesce=True,
        max_instances=5,
        next_run_time=ulity.now(),
    )

    # 每天04:00:00执行
    scheduler.add_job(
        func=fresher.fresh_single_tasks,
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
    app.state.mail_sender = MailSender()
    await app.state.mail_sender.start()

    scheduler_do(app)

    yield

    await app.state.mail_sender.stop()
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
app.include_router(mail.router, prefix="/mail")

@app.get("/")
async def index(request: Request):
    return RedirectResponse("/index")

@app.post("/logout")
async def logout():
    response = JSONResponse({"message": "logout success"})
    response = auth.del_user_from_cookie(response)
    return response


