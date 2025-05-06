import json
import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from difflib import SequenceMatcher


class Command(BaseCommand):
    help = '根据 abstract_pre_courses 字段匹配课程名称，并更新 match_pre_courses'

    def handle(self, *args, **kwargs):
        # 输入和输出文件路径
        input_file_path = os.path.join(settings.BASE_DIR, 'data', 't_course.xlsx')
        output_file_path = os.path.join(settings.BASE_DIR, 'data', 't_course6.csv')

        # 读取Excel文件
        df = pd.read_excel(input_file_path)

        # 生成课程名称列表用于匹配
        course_names = df['name'].tolist()

        # 逐行处理 DataFrame
        df['match_pre_courses'] = df['abstract_pre_courses'].apply(self.match_courses, args=(course_names,))

        # 保存结果为CSV
        df.to_csv(output_file_path, index=False, encoding='utf-8')

        self.stdout.write(self.style.SUCCESS(f'Successfully processed and saved to {output_file_path}'))

    def match_courses(self, abstract_pre_courses, course_names):
        """ 根据 abstract_pre_courses 中的内容匹配课程名称，并生成 match_pre_courses """
        if not abstract_pre_courses:
            return []

        # 清理和修复可能的格式问题
        abstract_pre_courses = self.clean_json_string(abstract_pre_courses)

        # 将 abstract_pre_courses 从 JSON 格式转换为 Python 列表
        try:
            abstract_courses = json.loads(abstract_pre_courses)
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'JSONDecodeError in abstract_pre_courses: {abstract_pre_courses}, error: {e}'))
            return ['格式错误']

        matched_courses = []

        # 遍历 abstract_courses，进行匹配
        for course in abstract_courses:
            # 尝试匹配最接近的课程名
            matched_course = self.find_best_match(course, course_names)

            if matched_course:
                matched_courses.append(matched_course)

        return matched_courses

    def find_best_match(self, course, course_names):
        """ 使用更复杂的匹配机制，返回最接近的值 """
        course = course.strip()  # 去除空格

        # 完全匹配
        if course in course_names:
            return course

        # 使用词语相似度（基于 SequenceMatcher）
        best_match = None
        best_score = 0.0

        for name in course_names:
            # 计算两个字符串的相似度（0到1之间的值，值越大表示越相似）
            score = self.calculate_similarity(course, name)

            if score > best_score:
                best_score = score
                best_match = name

        # 如果相似度足够高（例如大于0.7），则返回匹配结果
        if best_score > 0.5:
            return best_match

        return None  # 无匹配

    def calculate_similarity(self, str1, str2):
        """ 计算两个字符串的相似度，使用 SequenceMatcher """
        return SequenceMatcher(None, str1, str2).ratio()

    def clean_json_string(self, json_str):
        """ 修复潜在的格式问题，如多余的逗号或其他不符合JSON格式的内容 """
        # 清理末尾多余的逗号
        json_str = json_str.strip()

        # 处理单引号和双引号问题，确保符合有效的 JSON 格式
        json_str = json_str.replace("''", '"')  # 将两引号替换为双引号

        # 去除尾部可能存在的额外逗号
        if json_str.endswith(','):
            json_str = json_str[:-1]

        # 再次确保符合 JSON 格式
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"修复后的JSON解析错误: {json_str}, 错误: {e}"))

        return json_str
