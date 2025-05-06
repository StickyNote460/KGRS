import csv
import json
import os
import unicodedata
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Convert unicode escaped characters in JSON fields to readable Chinese characters'

    def handle(self, *args, **kwargs):
        # 读取原始CSV文件
        input_file_path = os.path.join(settings.BASE_DIR, 'data', 'export', 'course.csv')
        output_file_path = os.path.join(settings.BASE_DIR, 'data', 'import', 't_course.csv')

        # 处理CSV文件
        with open(input_file_path, 'r', encoding='utf-8') as infile, open(output_file_path, 'w', newline='',
                                                                          encoding='utf-8') as outfile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)

            # 写入CSV头
            writer.writeheader()

            # 逐行处理数据
            for row in reader:
                # 处理 abstract_pre_courses 字段
                if row['abstract_pre_courses']:
                    row['abstract_pre_courses'] = self.decode_unicode(row['abstract_pre_courses'])

                # 处理 match_pre_courses 字段
                if row['match_pre_courses']:
                    row['match_pre_courses'] = self.decode_unicode(row['match_pre_courses'])

                # 写入处理后的行
                writer.writerow(row)

            self.stdout.write(self.style.SUCCESS(f'Successfully processed and saved to {output_file_path}'))

    def decode_unicode(self, unicode_str):
        """ 将Unicode转义字符转换为可读的中文 """
        # 将JSON字符串解析为Python对象（列表或字典）
        decoded_str = json.loads(unicode_str)
        # 返回解码后的字符串（可以直接返回）
        return decoded_str
