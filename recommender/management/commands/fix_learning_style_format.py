# fix_learning_style_format.py
import os
import json
import logging
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KGRS.settings')
import django

django.setup()

from recommender.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "修复三重编码的Unicode转义问题"

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='每批处理的数据量'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='试运行模式'
        )

    def handle(self, *args, **options):
        self.batch_size = options['batch_size']
        self.dry_run = options['dry_run']

        try:
            with transaction.atomic():
                if self.dry_run:
                    self.stdout.write(self.style.WARNING("试运行模式，不会修改数据库"))
                    transaction.set_rollback(True)

                total_users = User.objects.count()
                qs = User.objects.all().order_by('id')

                with tqdm(total=total_users, desc="修复进度") as pbar:
                    for offset in range(0, total_users, self.batch_size):
                        batch = list(qs[offset:offset + self.batch_size])
                        self.process_batch(batch, pbar)

                self.stdout.write(self.style.SUCCESS("处理完成！"))
                self.show_sample()

        except Exception as e:
            logger.error(f"处理失败: {str(e)}", exc_info=True)
            raise

    def process_batch(self, batch, pbar):
        """增强容错处理"""
        processed = 0
        error_count = 0
        for user in batch:
            try:
                original = user.learning_style
                if not original or original == 'null':
                    continue

                logger.debug(f"原始数据: {original[:50]}...")

                fixed_value = self.fix_double_encoded_unicode(original)

                logger.debug(f"转换后数据: {fixed_value[:50]}...")

                if self.validate_fix(original, fixed_value):
                    user.learning_style = fixed_value
                    processed += 1
                else:
                    error_count += 1
                    with open("error_cases.txt", "a") as f:
                        f.write(f"用户 {user.id} 原始数据: {original}\n")
                        f.write(f"转换结果: {fixed_value}\n\n")

            except Exception as e:
                logger.error(f"处理用户 {user.id} 时发生致命错误: {str(e)}")
                error_count += 1

        pbar.update(len(batch))
        pbar.set_postfix_str(f"成功: {processed} 失败: {error_count}")

        if not self.dry_run:
            User.objects.bulk_update(batch, ['learning_style'])

    def fix_double_encoded_unicode(self, raw_str):
        """处理三重编码的特殊情况"""
        try:
            # 第一次解码：转换转义字符
            step1 = raw_str.encode('latin-1').decode('unicode_escape')

            # 提取所有Unicode编码点
            hex_values = re.findall(r'\\u00([a-fA-F0-9]{2})', step1)

            # 构建字节序列
            byte_sequence = bytes(int(x, 16) for x in hex_values)

            # 第二次解码：UTF-8解码
            step2 = byte_sequence.decode('utf-8')

            # 第三次处理：清理残留转义
            step3 = step2.encode('latin-1').decode('utf-8')

            # 转换为标准JSON
            return json.dumps(json.loads(step3), ensure_ascii=False)

        except Exception as e:
            logger.error(f"深度解码失败: {raw_str[:50]}... 错误: {str(e)}")
            return raw_str

    def validate_fix(self, original, fixed):
        """增强型验证"""
        try:
            data = json.loads(fixed)

            # 中文检测
            if not any('\u4e00' <= c <= '\u9fff' for c in json.dumps(data)):
                raise ValueError("未检测到有效中文")

            # 数值验证
            if not all(0 <= v <= 1 for v in data.values()):
                raise ValueError("数值范围异常")

            return True
        except Exception as e:
            logger.warning(f"验证失败: {str(e)}")
            return False

    def show_sample(self):
        """显示修复样本"""
        sample = User.objects.first()
        if sample:
            self.stdout.write("\n样本数据验证:")
            try:
                self.stdout.write(f"原始值: {sample.learning_style[:100]}...")
                data = json.loads(sample.learning_style)
                self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
            except:
                self.stdout.write(self.style.ERROR("样本数据格式异常"))