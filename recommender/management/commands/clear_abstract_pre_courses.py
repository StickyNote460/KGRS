import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = '将 abstract_pre_courses 字段置为空 JSON 对象'

    def handle(self, *args, **kwargs):
        # 输入和输出文件路径
        input_file_path = os.path.join(settings.BASE_DIR, 'data', 't_course4.csv')
        output_file_path = os.path.join(settings.BASE_DIR, 'data', 't_course7.csv')

        # 读取CSV文件
        df = pd.read_csv(input_file_path)

        # 将 abstract_pre_courses 字段置为空 JSON 对象
        df['abstract_pre_courses'] = [{} for _ in range(len(df))]

        # 保存更新后的数据到新的CSV文件
        df.to_csv(output_file_path, index=False, encoding='utf-8')

        self.stdout.write(self.style.SUCCESS(f'Successfully processed and saved to {output_file_path}'))
