from django.core.management.base import BaseCommand
from recommender.kg.transE_data import TransEDataLoader

class Command(BaseCommand):
    help = '生成 TransE 数据并保存为 txt 文件'

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write(self.style.SUCCESS('🚀 正在生成 TransE 数据...'))
            loader = TransEDataLoader()
            loader.save_to_txt()
            self.stdout.write(self.style.SUCCESS('✅ 成功生成并保存数据！'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ 错误: {str(e)}'))
