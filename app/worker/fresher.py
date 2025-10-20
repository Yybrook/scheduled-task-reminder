import datetime
import logging
from fastapi import FastAPI
from app.routers.mail import MailSender, MailInfo, format_mail_task
from app.models.models import ScheduledTask
from app import ulity

_logger = logging.getLogger(__name__)


async def fresh_email_remind(app: FastAPI):
    """轮询所有任务，发送邮件提醒，一分钟执行一次"""
    try:
        _now = ulity.now()
        # 获取 task
        tasks = await ScheduledTask.all().prefetch_related("user")
        # 从 app 中获取发送器
        mail_sender: MailSender = app.state.mail_sender

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
                if task.user.email:
                    mail_info = MailInfo(
                        to=task.user.email,
                        subject=f"[正式提醒] {task.name}",
                        username=task.user.username,
                        task_name=task.name,
                        message=task.message,
                        task_datetime=_task_dt,
                        task_done=task.current_done_times + 1,
                        repeat_type=task.repeat_type_str,
                        note="正式提醒",
                        local_image_path="app/statics/logo.jpg"
                    )
                    mail_task = format_mail_task(mail_info)
                    await mail_sender.add_task(mail_task)

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
                        if task.user.email:
                            mail_info = MailInfo(
                                to=task.user.email,
                                subject=f"[提前{day}天] {task.name}",
                                username=task.user.username,
                                task_name=task.name,
                                message=task.message,
                                task_datetime=_task_dt,
                                task_done=task.current_done_times + 1,
                                repeat_type=task.repeat_type_str,
                                note=f"提前{day}天提醒",
                                local_image_path="app/statics/logo.jpg"
                            )
                            mail_task = format_mail_task(mail_info)
                            await mail_sender.add_task(mail_task)

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
