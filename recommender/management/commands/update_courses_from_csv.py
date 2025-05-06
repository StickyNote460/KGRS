import os
import pandas as pd
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from recommender.models import Course  # Make sure to replace 'your_app' with your actual app name

class Command(BaseCommand):
    help = '将 CSV 文件中的 match_pre_courses 和 abstract_pre_courses 字段更新到数据库，确保它们是有效的 JSON 格式'

    def handle(self, *args, **kwargs):
        # 输入文件路径
        input_file_path = os.path.join(settings.BASE_DIR, 'data', 't_course4.csv')

        # 读取CSV文件
        df = pd.read_csv(input_file_path)

        # 遍历每一行数据
        for _, row in df.iterrows():
            course_id = row['id']  # 假设 `id` 列是课程的唯一标识
            match_pre_courses = self.convert_to_json(row['match_pre_courses'])
            abstract_pre_courses = self.convert_to_json(row['abstract_pre_courses'])

            try:
                # 查找对应的课程记录
                course = Course.objects.get(id=course_id)
                # 更新 match_pre_courses 和 abstract_pre_courses 字段
                course.match_pre_courses = match_pre_courses
                course.abstract_pre_courses = abstract_pre_courses
                course.save()  # 保存更改
                self.stdout.write(self.style.SUCCESS(f'更新成功: {course_id}'))
            except Course.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'未找到课程: {course_id}'))

    def convert_to_json(self, value):
        """ 转换字段为 JSON 格式，如果字段为空则返回空数组或空字典 """
        if pd.isna(value) or value == '':
            return []  # 空字符串或空值转换为空数组
        try:
            # 替换字符串中的单引号为双引号
            value = value.replace("'", '"')
            # 解析字符串为 JSON 对象
            return json.loads(value)  # 尝试将字符串解析为 JSON
        except json.JSONDecodeError:
            return []  # 如果无法解析为 JSON，返回空数组
