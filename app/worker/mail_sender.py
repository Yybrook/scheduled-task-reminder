import asyncio
import traceback
from app.ulity import send_email_with_win32


class MailSender:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=1)
        self._worker_task = None

    async def start(self):
        """启动后台邮件发送任务"""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        """停止任务"""
        await self.queue.put(None)
        if self._worker_task:
            await self._worker_task

    async def _worker(self):
        while True:
            try:
                task = await self.queue.get()
                # 退出信号
                if task is None:
                    break

                # 发送邮件
                '''
                to:
                local_image_path:
                subject: 邮件主题
                context: 邮件内容字典
                    "username": task.user.username,
                    "task_name": task.task_name,
                    "message": task.message,
                    "task_datetime": dt,
                    "task_done": task.current_repeat_done,
                    "repeat_type": repeat_type,
                    "note": "正式提醒"
                cc:
                sender:
                '''
                await send_email_with_win32(
                    to=task["to"],
                    subject=task["subject"],
                    context=task["context"],
                    local_image_path=task.get("local_image_path", None),
                    cc=task.get("cc", None),
                    sender=task.get("sender", None),
                )

            except Exception as err:
                print(f"send email error: {traceback.format_exc()}")
            finally:
                self.queue.task_done()

    async def add_task(self, task: dict):
        await self.queue.put(task)
