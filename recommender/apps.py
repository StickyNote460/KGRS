from django.apps import AppConfig
#RecommenderConfig.ready() 是Django应用的初始化入口
#必须在ready()中导入信号模块才能注册接收器

class RecommenderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recommender'

    def ready(self):
        """正确的缩进（与class块对齐）"""
        # 添加运行环境判断
        if not self._is_development_server():
            print("[正式模式] 注册信号处理器")
            self._register_signals()
        else:
            print("[开发模式] 跳过重复注册")

    def _register_signals(self):
        """安全的信号注册方法"""
        import recommender.signals

    @classmethod
    def _is_development_server(cls):
        """判断是否开发环境"""
        from sys import argv
        return 'runserver' in argv