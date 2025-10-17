import datetime
import typing
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from app.worker.mail_sender import MailSender

router = APIRouter()

class MailInfo(BaseModel):
    to: typing.Union[EmailStr, list[EmailStr]]
    cc: typing.Union[EmailStr, list[EmailStr], None] = None
    sender: typing.Union[EmailStr, None] = None
    subject: str
    username: str
    task_name: str
    message: str
    task_datetime: datetime.datetime
    task_done: int
    repeat_type: str
    note: str
    local_image_path: typing.Optional[str] = None

def format_mail_task(mail_info: MailInfo) -> dict:
    '''
    to:
    cc:
    sender:
    subject: 邮件主题
    context: 邮件内容字典
        "username": task.user.username,
        "task_name": task.task_name,
        "message": task.message,
        "task_datetime": dt,
        "task_done": task.current_repeat_done,
        "repeat_type": repeat_type,
        "note": "正式提醒"
    local_image_path:
    '''
    task = {
        "to": mail_info.to,
        "cc": mail_info.cc,
        "sender": mail_info.sender,
        "subject": mail_info.subject,
        "context": {
            "username": mail_info.username,
            "task_name": mail_info.task_name,
            "message": mail_info.message,
            "task_datetime": mail_info.task_datetime.strftime("%Y-%m-%d %H:%M"),
            "task_done": mail_info.task_done,
            "repeat_type": mail_info.repeat_type,
            "note": mail_info.note,
        },
        "local_image_path": mail_info.local_image_path,
    }
    return task

@router.post("/")
async def send_mail(request: Request, mail_info: MailInfo):
    """用户接口：异步发送任务提醒邮件"""
    try:
        mail_task = format_mail_task(mail_info)
        mail_sender: MailSender = request.app.state.mail_sender
        await mail_sender.add_task(mail_task)

        return {"success": True, "message": "邮件任务添加成功"}
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"邮件任务添加失败: {err}")
