from django.apps import AppConfig
#RecommenderConfig.ready() 是Django应用的初始化入口
#必须在方法ready()中导入信号模块才能注册接收器

class RecommenderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    #指定Django模型默认的主键字段类型。
    # BigAutoField是一个64位整数类型，适用于大型项目，避免主键溢出。
    name = 'recommender'
    #指定该应用配置对应的Django应用的名称
    # 必须与应用的名称一致！！！

    def ready(self):
        """正确的缩进（与class块对齐）"""
        pass  # 暂时禁用信号
    #     # 添加运行环境判断
    #     if not self._is_development_server():
    #         print("[正式模式] 注册信号处理器")
    #         self._register_signals()
    #     else:
    #         print("[开发模式] 跳过重复注册")
    #
    # def _register_signals(self):
    #     """安全的信号注册方法"""
    #     #导入recommender.signals模块
    #     import recommender.signals
    #
    # @classmethod
    # def _is_development_server(cls):
    #     """判断是否开发环境"""
    #     #通过判断`sys.argv`中是否包含`runserver`命令
    #     #在不同环境下执行不同的初始化逻辑
    #     '''
    #     开发环境跳过注册的原因:
    #     问题核心：Django 开发服务器在代码修改后会自动重启，导致：
    #     ready() 方法被多次调用
    #     信号处理器重复注册
    #     同一信号被多次处理
    #     '''
    #     from sys import argv
    #     return 'runserver' in argv