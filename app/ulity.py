import typing
import base64
import datetime
import zoneinfo
import bcrypt
import smtplib
import asyncio
import json
from PIL import Image
import io
import jinja2
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from app.env import settings



# jinja2环境
jinja2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("./statics"),
    autoescape=True
)


########################################################################
# 时间
########################################################################
def now(tz: typing.Optional[str]="Asia/Shanghai"):
    """获取当前时间"""
    if tz is None:
        _now = datetime.datetime.now()
    else:
        _now = datetime.datetime.now(tz=zoneinfo.ZoneInfo(tz))
    return _now

def form_datetime(date: str, time: str, tz: typing.Optional[str]="Asia/Shanghai") -> typing.Optional[datetime.datetime]:
    """
    将 date 和 time 字符串组合成 datetime 对象
    :param date: %Y-%m-%d
    :param time: %H:%M
    :param tz: 时区, "Asia/Shanghai" or None
    :return:
    """
    dt_str = f"{date} {time}:00"
    dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    # 指定时区
    if tz:
        dt = dt.replace(tzinfo=zoneinfo.ZoneInfo(tz))
    return dt

########################################################################
# 邮件提醒
########################################################################
def dumps_advance_days(days: list) -> str:
    """
    将提醒天数列表转换为 json字符串，json list
    :param days: [1,2,7]
    :return:  [1,2,7]
    """
    days = [int(day) for day in days]
    return json.dumps(sorted(days))

def loads_advance_days(days: str) -> list:
    """
    将 advance_days json字符串（例如 '[1, 2, 7]') 转成整数列表 [1,2,7]
    :return:
    """
    advance_days = json.loads(days)
    advance_days = [int(day) for day in advance_days]
    return sorted(advance_days)

def init_advance_status(days: typing.Union[str, list]) -> str:
    """
    将提醒天数转化为提醒状态 json dict
    :param days: [1,2,7] | "1,2,7"
    :return:  {"1": False, "2": False, "7": False,}
    """
    if isinstance(days, str):
        days = loads_advance_days(days)
    else:
        days = [int(day) for day in days]
        days = sorted(days)
    status = {day: False for day in days}
    return dumps_advance_status(status)

def dumps_advance_status(status: dict) -> str:
    advance_status = json.dumps(status)
    return advance_status

def loads_advance_status(status: str) -> dict:
    _status = json.loads(status)
    return {int(k): v for k, v in _status.items()}

def image_to_data_uri(path: str, max_size=(150, 150)) -> str:
    """将图片压缩到指定大小，并转为 base64 data URI"""
    with Image.open(path) as img:
        img.thumbnail(max_size)  # 等比例缩小
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{encoded}"

async def send_email_html(email: str, subject: str, context: typing.Dict, local_image_path: str = None):
    """
    异步发送 HTML 邮件（使用 asyncio.to_thread 避免阻塞）
    :param email:
    :param local_image_path:
    :param subject: 邮件主题
    :param context: 邮件内容字典
                    "username": task.user.username,
                    "task_name": task.task_name,
                    "message": task.message,
                    "task_datetime": dt,
                    "task_done": task.current_repeat_done,
                    "repeat_type": repeat_type,
                    "note": "正式提醒"
    """
    if not settings.SMTP_SERVER or not settings.SMTP_USER or not email:
        raise ValueError("用户SMTP或Email未配置")

    # 生成图片 data URI
    img_data_uri = image_to_data_uri(local_image_path) if local_image_path else ""
    context["img_data_uri"] = img_data_uri

    # =============== Jinja2 模板渲染 ===============
    template = jinja2_env.get_template("/mail.html")
    body_html = template.render(context)

    # =============== 构建邮件 ===============
    msg = MIMEMultipart("alternative")
    msg['From'] = formataddr(("Schedule Task Reminder", settings.SMTP_USER))
    msg['To'] = formataddr((context.get("username", ""), email))
    msg['Subject'] = Header(subject, 'utf-8')

    # 纯文本（防止客户端不支持 HTML）
    text_part = MIMEText("任务提醒，请查看邮件内容。", "plain", "utf-8")
    html_part = MIMEText(body_html, "html", "utf-8")

    msg.attach(text_part)
    msg.attach(html_part)

    # =============== 同步发送函数（放到线程池） ===============
    def _send():
        with smtplib.SMTP_SSL(settings.SMTP_SERVER,settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [email,], msg.as_string())
            try:
                server.quit()
            # 忽略 QQ 邮箱关闭连接时的异常
            except smtplib.SMTPResponseException:
                pass

    # 使用 asyncio.to_thread 在异步环境下执行同步函数
    await asyncio.to_thread(_send)

########################################################################
# User
########################################################################
def get_hashed_pwd(password: str) -> str:
    """密码转换为 hash 值"""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")
