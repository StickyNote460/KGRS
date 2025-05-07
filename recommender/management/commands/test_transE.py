from django.core.management.base import BaseCommand
from recommender.recommendations.graph_based.transE_path_finder import TransEPathFinder
from recommender.models import User, Course


class Command(BaseCommand):
    help = '测试TransE路径推荐'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, required=True)
        parser.add_argument('--course', type=str, required=True)

    def handle(self, *args, **options):
        # 获取或创建用户
        try:
            user = User.objects.get(name=options['user'])
        except User.DoesNotExist:
            user = User.objects.create(
                id=f"temp_{options['user']}",
                name=options['user'],
                learning_style={}
            )

        # 获取目标课程
        try:
            course = Course.objects.get(name=options['course'])
        except Course.DoesNotExist:
            return self.stdout.write(self.style.ERROR("目标课程不存在"))

        # 执行推荐
        finder = TransEPathFinder()
        path = finder.find_path(user.id, course.id)

        self.stdout.write(self.style.SUCCESS("推荐路径："))
        for node in path:
            if node.startswith('course_'):
                name = Course.objects.get(id=node).name
            else:
                name = node
            self.stdout.write(f"→ {name}")