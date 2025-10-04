import typing
import bcrypt
import datetime
from dateutil import relativedelta
from tortoise import fields
from tortoise.models import Model
from tortoise.transactions import in_transaction

from app import ulity


########################################################################
# Tortoise ORM 模型
########################################################################

class User(Model):
    id = fields.IntField(pk=True)
    # 用户名
    username = fields.CharField(max_length=100, unique=True)
    # 密码 hash
    password_hash = fields.CharField(max_length=200)
    # 邮箱
    email = fields.CharField(max_length=200, null=True)
    # 创建时间
    created_at = fields.DatetimeField(auto_now_add=True)

    # 类型提示, 不在数据库里生成字段
    scheduled_tasks: fields.ReverseRelation["ScheduledTask"]
    single_tasks: fields.ReverseRelation["SingleTask"]

    def is_pwd_correct(self, password: str) -> bool:
        """密码是否正确"""
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

class ScheduledTask(Model):
    id = fields.IntField(pk=True)

    # 关联用户，多对一关系
    user = fields.ForeignKeyField("models.User", related_name="scheduled_tasks")

    # 任务名称
    name = fields.CharField(max_length=100)
    # 任务信息
    message = fields.TextField()

    # 创建时间
    created_at = fields.DatetimeField(auto_now_add=True)

    # 任务是否结束
    is_ended = fields.BooleanField(default=False)
    # 结束时间
    ended_at = fields.DatetimeField(null=True)

    # 任务开始时间
    start_datetime = fields.DatetimeField()

    # 重复设置
    # 'none' | 'days' | 'weeks' | 'months' | 'years'
    repeat_type = fields.CharField(max_length=20, default='none')
    # repeat_interval<0 -> 不重复
    # repeat_interval=0 -> 每天/周/月/年
    # repeat_interval=X -> 每隔X+1天/周/月/年
    repeat_interval = fields.IntField(default=-1)
    # 重复需求
    # repeat_times<=0 -> 表示无限重复
    repeat_times = fields.IntField(default=-1)

    # 提前提醒天数，字符串，例如 "1,2,7"
    _advance_days = fields.CharField(max_length=100, default='')

    # 当前任务时间: 指向下一次wei
    current_task_datetime = fields.DatetimeField()
    # 已重复次数
    current_done_times = fields.IntField(default=0)
    # 提前提醒状态，JSON 字符串，记录哪些提前天数已提醒
    _current_advance_status = fields.TextField(default='{}')

    # 类型提示, 不在数据库里生成字段
    single_tasks: fields.ReverseRelation["SingleTask"]


    @property
    def is_alive(self) -> bool:
        # 任务已经标记结束
        if self.is_ended:
            return False
        # 1. 设置了重复次数要求
        # 2. 当前重复次数大于要求
        if 0 < self.repeat_times <= self.current_done_times:
            return False
        # 不重复，且 当前时间大于任务时间
        if self.repeat_interval < 0 and ulity.now() > self.current_task_datetime:
            return False
        return True

    @property
    def has_next_task(self):
        # 不存活
        if not self.is_alive:
            return False
        # 不重复
        if self.repeat_interval < 0:
            return False
        return True

    def end(self, end: bool):
        self.is_ended = end
        if end:
            self.ended_at = ulity.now()
        else:
            self.ended_at = None

    @property
    def advance_days(self):
        """将 advance_days JSON 字符串转换为 list"""
        try:
            return ulity.loads_advance_days(self._advance_days)
        except:
            return list()

    def set_advance_days(self, days: list):
        # input -> [1,2,7]
        self._advance_days = ulity.dumps_advance_days(days)

    @property
    def current_advance_status(self) -> dict:
        """将 advance_status JSON 字符串转换为 dict"""
        try:
            return ulity.loads_advance_status(self._current_advance_status)
        except:
            return dict()

    def set_current_advance_status(self, status: dict):
        # input -> {"1": True, "2": False, "7": False}
        self._current_advance_status = ulity.dumps_advance_status(status)

    def reset_current_advance_status(self):
        """
        重置提前提醒状态 -> advance_status = {"1": False, "2": False, "7": False}
        :return:
        """
        self._current_advance_status = ulity.init_advance_status(self._advance_days)

    def next_datetime(self, dt: typing.Union[datetime.datetime] = None) -> typing.Optional[datetime.datetime]:
        """下一个任务时间"""
        # 不重复
        if self.repeat_interval < 0:
            return None

        if dt is None:
            dt = self.current_task_datetime
        # 天
        if self.repeat_type == 'days':
            return dt + relativedelta.relativedelta(days=self.repeat_interval + 1)
        # 周
        elif self.repeat_type == 'weeks':
            return dt + relativedelta.relativedelta(weeks=self.repeat_interval + 1)
        # 月
        elif self.repeat_type == 'months':
            return dt + relativedelta.relativedelta(months=self.repeat_interval + 1)
        # 年
        elif self.repeat_type == 'years':
            return dt + relativedelta.relativedelta(years=self.repeat_interval + 1)
        # 无效
        else:
            return None

    def last_datetime(self, dt: typing.Union[datetime.datetime] = None) -> typing.Optional[datetime.datetime]:
        """前一个任务时间"""
        if dt is None:
            dt = self.current_task_datetime

        # 天
        if self.repeat_type == 'days':
            last_dt =  dt - relativedelta.relativedelta(days=self.repeat_interval + 1)
            threshold = self.start_datetime - relativedelta.relativedelta(days=self.repeat_interval + 1)
        # 周
        elif self.repeat_type == 'weeks':
            last_dt =  dt - relativedelta.relativedelta(weeks=self.repeat_interval + 1)
            threshold = self.start_datetime - relativedelta.relativedelta(weeks=self.repeat_interval + 1)
        # 月
        elif self.repeat_type == 'months':
            last_dt =  dt - relativedelta.relativedelta(months=self.repeat_interval + 1)
            threshold = self.start_datetime - relativedelta.relativedelta(months=self.repeat_interval + 1)
        # 年
        elif self.repeat_type == 'years':
            last_dt =  dt - relativedelta.relativedelta(years=self.repeat_interval + 1)
            threshold = self.start_datetime - relativedelta.relativedelta(years=self.repeat_interval + 1)
        # 无效
        else:
            return None

        if last_dt >= threshold:
            return last_dt
        else:
            return None

    def next_single_task_datetime(self, start_dt: typing.Union[datetime.datetime] = None) -> typing.Optional[datetime.datetime]:
        """
        获取下一次任务时间
        :param start_dt:   起始时间，如果是None，从task.current_task_datetime开始
        :return:
        """
        # todo 优化两个 while true
        if start_dt is None:
            # 没有下一个任务
            if not self.has_next_task:
                return None
            else:
                return self.next_datetime()
        else:
            # 小于任务起始时间 -> start_datetime
            if start_dt < self.start_datetime:
                return self.start_datetime
            # 大于等于任务起始时间
            else:
                # 不重复
                if self.repeat_interval < 0:
                    return None
                else:
                    # 当前任务时间
                    cur_dt = self.current_task_datetime
                    # 当前重复次数
                    cur_times = self.current_done_times

                    # 小于当前时间
                    if start_dt < cur_dt:
                        while True:
                            last_dt = self.last_datetime(cur_dt)
                            # 没有前一个任务
                            if last_dt is None:
                                return None
                            else:
                                # 前一个任务 小于等于 start_dt
                                if last_dt <= start_dt:
                                    return cur_dt
                                else:
                                    cur_dt = last_dt
                    # 大于等于当前时间
                    else:
                        # 没有下一个任务
                        if not self.has_next_task:
                            return None
                        else:
                            while True:
                                next_dt = self.next_datetime(cur_dt)
                                cur_times += 1
                                # 超过重复需求
                                if 0 < self.repeat_times <= cur_times:
                                    return None
                                else:
                                    # 下一个任务时间 大于 起始时间
                                    if next_dt > start_dt:
                                        return next_dt
                                    else:
                                        cur_dt = next_dt

    def fresh_next_task(self) -> typing.Optional[datetime.datetime]:
        """
        以当下为基准，刷新下一次任务是时间
        :return:
        """
        now = ulity.now()
        # 获取当前任务时间
        cur_task_dt = self.current_task_datetime
        # 当前任务时间 > now
        if cur_task_dt > now:
            return cur_task_dt
        else:
            # 下一次任务时间
            next_task_dt = self.next_single_task_datetime()
            # 任务彻底结束 -> 自动标记为结束任务
            if next_task_dt is None:
                self.is_ended = True
                self.ended_at = cur_task_dt
            # 任务没结束，刷新
            else:
                self.current_task_datetime = next_task_dt
                self.current_done_times += 1
                self.reset_current_advance_status()

            return next_task_dt

    async def generate_single_tasks(self, days_ahead: int = 365):
        """
        根据 ScheduledTask 生成未来 days_ahead 天的 single_tasks
        :param days_ahead: 生成未来多少天的任务
        """
        single_tasks = list()

        # 任务时间
        cur_task_dt = self.current_task_datetime
        # 使能时间：当前时间 + days_ahead
        enable_dt = ulity.now() + datetime.timedelta(days=days_ahead)

        # 使能的最新任务时间
        enable_last_task = await SingleTask.filter(task=self).order_by("-datetime").first()

        if enable_last_task:
            start_dt = self.next_single_task_datetime(enable_last_task.datetime)
            if start_dt is None:
                return
            repeat_times = enable_last_task.repeat_times
            next_done_times = enable_last_task.done_times + 1
        else:
            start_dt = cur_task_dt
            repeat_times = self.repeat_times
            next_done_times = self.current_done_times + 1

        while start_dt <= enable_dt:
            single_tasks.append(
                SingleTask(
                    user_id=self.user_id,
                    task=self,
                    datetime=start_dt,       # 任务时间
                    done_times=next_done_times, # 完成次数
                    repeat_times=repeat_times,  # 还剩次数，-1表示无限
                    is_done=False,      # 是否完成
                    done_at=None,       # 完成时间
                    remark=None,
                )
            )

            # 计算下一个提醒时间
            next_dt = self.next_single_task_datetime(start_dt)
            if next_dt is None:
                break

            start_dt = next_dt
            next_done_times += 1

        # 批量插入
        if single_tasks:
            async with in_transaction():
                await SingleTask.bulk_create(single_tasks)

    @property
    def repeat_type_str(self) -> str:
        if self.repeat_interval < 0:
            return "无"

        if self.repeat_type == "days":
            repeat_type = "天"
        elif self.repeat_type == "weeks":
            repeat_type = "周"
        elif self.repeat_type == "months":
            repeat_type = "月"
        elif self.repeat_type == "years":
            repeat_type = "年"
        else:
            return "无"

        if self.repeat_interval == 0:
            return f"每{repeat_type}"
        else:
            return f"间隔{self.repeat_interval}{repeat_type}"

class SingleTask(Model):
    """
    每次提醒对应的具体时间，支持按日期查询
    """
    id = fields.IntField(pk=True)

    # 关联用户，多对一关系
    user = fields.ForeignKeyField("models.User", related_name="single_tasks")
    # 每个小项目
    task = fields.ForeignKeyField("models.ScheduledTask", related_name="single_tasks")

    # 任务时间
    datetime = fields.DatetimeField()
    # 已重复次数
    done_times = fields.IntField()

    # 任务备注信息
    remark = fields.TextField(null=True)

    # 重复需求
    # repeat_times<=0 -> 表示无限重复
    repeat_times = fields.IntField()

    # 是否完成
    is_done = fields.BooleanField(default=False)
    # 完成时间
    done_at = fields.DatetimeField(null=True)

    def done(self, done: bool):
        self.is_done = done
        if done:
            self.done_at = ulity.now()
        else:
            self.done_at = None