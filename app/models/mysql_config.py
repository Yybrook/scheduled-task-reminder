from app.env import settings

MYSQL_TORTOISE_ORM = {
    'connections': {
        'default': {
            'engine': 'tortoise.backends.mysql',  # MySQL or Mariadb
            'credentials': {
                'host': settings.SQL_HOST,
                'port': settings.SQL_PORT,
                'user': settings.SQL_USER,
                'password': settings.SQL_PASSWORD,
                'database': settings.SQL_DATABASE,
                'charset': 'utf8mb4',
                "echo": True
            }
        },
    },
    'apps': {
        'models': {
            'models': ['app.models.models', "aerich.models"],
            'default_connection': 'default',
        }
    },
    'use_tz': False,
    'timezone': 'Asia/Shanghai'
}


# 1. 安装: pip install aerich
# 2. 初始化配置: aerich init -t app.models.mysql_config.MYSQL_TORTOISE_ORM
#    生成 -> pyproject.toml: 保存配置文件路径; migrations: 存放迁移文件
# 3. 初始化数据库: aerich init-db
# 4. 更新模型并进行迁移: aerich migrate --name XXX
#    重新执行迁移, 写入数据库: aerich upgrade
# 5. 回到上一个版本: aerich downgrade
# 6. 查看历史迁移记录: aerich history


if __name__ == '__main__':
    print(MYSQL_TORTOISE_ORM)