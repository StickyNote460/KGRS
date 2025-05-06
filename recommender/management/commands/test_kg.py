from django.core.management.base import BaseCommand
from recommender.models import User
from recommender.recommendations.graph_based.path_finder import PathFinder

class Command(BaseCommand):
    help = '测试 PathFinder 功能'

    def handle(self, *args, **kwargs):
        # 获取已存在的用户（假设用户名是 "程贝"）
        try:
            user = User.objects.get(name='李喜锋')  # 根据用户名查找用户
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("用户 '杜秀莉' 不存在"))
            return

        # 创建 PathFinder 实例并查找路径
        path_finder = PathFinder(target_course_id='C_course-v1:BIT+PHY1701702+sp')
        recommended_path = path_finder.find_optimal_path(user)

        print(f"推荐的路径是: {recommended_path}")
