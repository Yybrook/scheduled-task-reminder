import typing
import datetime
from fastapi import Request, HTTPException, Response
from app.models.models import User
from app import ulity



# 全局变量
# 简易 session 存储，key=user_id, value=datetime
SESSION_STORE = dict()
SESSION_EXPIRE_MINUTES = 30
# todo SESSION后期考虑存储在redis中
"""
import aioredis
redis = await aioredis.from_url("redis://localhost")
async def set_session(user_id: int):
    expire = SESSION_EXPIRE_MINUTES * 60
    await redis.set(f"session:{user_id}", "1", ex=expire)
async def check_session(user_id: int):
    return await redis.exists(f"session:{user_id}")
"""


async def get_user_from_request(request: Request) -> User:
    """从 cookie 获取当前登录用户"""
    user_id = get_user_from_cookie(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")
    return await get_user_by_id(user_id)

async def get_user_by_id(user_id: int) -> User:
    """根据 user_id 从数据库查询 用户信息"""
    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

def get_user_from_cookie(request: Request) -> typing.Optional[int]:
    """从cookies中获取用户id"""
    # 从 cookies 中获取
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    user_id = int(user_id)
    # SESSION_STORE 中无
    if user_id not in SESSION_STORE:
        return None
    # SESSION 过期
    expire_time = SESSION_STORE[user_id]
    if ulity.now() >= expire_time:
        return None
    # 刷新 SESSION 过期时间
    SESSION_STORE[user_id] = ulity.now() + datetime.timedelta(minutes=SESSION_EXPIRE_MINUTES)
    return user_id

def create_session(user_id: int) -> str:
    """创建 session 并返回 session key"""
    expire_time = ulity.now() + datetime.timedelta(minutes=SESSION_EXPIRE_MINUTES)
    SESSION_STORE[user_id] = expire_time
    return str(user_id)

def add_user_2_cookie(response: Response, user_id: typing.Union[int, str]):
    response.set_cookie(
        key="user_id",
        value=str(user_id),
        max_age=SESSION_EXPIRE_MINUTES * 60,
        httponly=True,  # JS 不能访问
        secure=False  # 若部署 HTTPS，可改 True
    )
    return response

def del_user_from_cookie(response: Response):
    response.delete_cookie(key="user_id")
    return response