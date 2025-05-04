# KGRS/recommender/management/commands/import_video_names.py
import json
import codecs
import logging
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm
from recommender.models import Course

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "将课程视频名称数据从JSON文件导入数据库"

    # 固定的文件路径配置
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # 项目根目录(KGRS)
    JSON_PATH = BASE_DIR / "data" / "raw" / "course.json"  # 原始数据路径
    DB_PATH = BASE_DIR / "db.sqlite3"  # 数据库路径

    def handle(self, *args, **kwargs):
        """主处理逻辑"""
        stats = {
            'processed': 0,
            'success': 0,
            'invalid_data': 0,
            'missing_course': 0,
            'errors': 0
        }

        try:
            # 验证文件存在性
            if not self.JSON_PATH.exists():
                raise FileNotFoundError(f"JSON文件不存在: {self.JSON_PATH}")

            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(f"数据库路径: {self.DB_PATH}")
            self.stdout.write(f"开始处理JSON文件: {self.JSON_PATH}\n")

            # 读取并解析JSON数据
            with open(self.JSON_PATH, 'r', encoding='utf-8') as f:
                try:
                    courses_data = json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {str(e)}")
                    raise

            total_items = len(courses_data)
            self.stdout.write(f"共发现 {total_items} 条课程数据")
            self.stdout.write("=" * 50 + "\n")

            # 事务处理保证数据一致性
            with transaction.atomic():
                with tqdm(
                        courses_data,
                        desc="处理进度",
                        unit="条",
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                ) as progress:
                    for idx, course_data in enumerate(progress, 1):
                        try:
                            # 数据验证阶段
                            if not self._validate_data(course_data):
                                stats['invalid_data'] += 1
                                continue

                            course_id = course_data['id']
                            raw_names = course_data['display_name']

                            # 数据清洗：过滤null值并转换类型
                            # video_names = [
                            #     str(name).strip()
                            #     for name in raw_names
                            #     if name is not None and isinstance(name, (str, int, float))
                            # ]
                            # 修改为（添加self._decode_item调用）
                            video_names = [
                                self._decode_item(str(name).strip())
                                for name in raw_names
                                if name is not None and isinstance(name, (str, int, float))
                            ]

                            # 去除空字符串
                            video_names = [name for name in video_names if name]

                            # 数据库操作
                            try:
                                course = Course.objects.get(id=course_id)
                                course.video_name = video_names
                                course.save()
                                stats['success'] += 1
                            except Course.DoesNotExist:
                                logger.warning(f"课程不存在 (行{idx}): {course_id}")
                                stats['missing_course'] += 1
                            except Exception as e:
                                logger.error(f"数据库错误 (行{idx}): {str(e)}")
                                stats['errors'] += 1

                            stats['processed'] += 1
                            progress.set_postfix({
                                '成功': stats['success'],
                                '无效数据': stats['invalid_data'],
                                '缺失课程': stats['missing_course']
                            })

                        except Exception as e:
                            logger.error(f"处理异常 (行{idx}): {str(e)}")
                            stats['errors'] += 1

        except Exception as e:
            logger.error(f"全局异常: {str(e)}")
            raise
        finally:
            self._print_summary(stats)

    def _decode_item(self, item):
        """处理双重编码的Unicode转义"""
        if isinstance(item, str):
            try:
                # 第一次解码：将字符串中的Unicode转义符转换为字节
                bytes_data = codecs.decode(item, 'unicode_escape').encode('latin1')
                # 第二次解码：将字节按UTF-8解码为正确中文
                return bytes_data.decode('utf-8')
            except Exception as e:
                logger.warning(f"解码失败: {str(e)}")
                return item  # 返回原始数据避免丢失
        return item

    def _validate_data(self, data):
        """数据验证（返回布尔值）"""
        # 必需字段检查
        required_fields = ['id', 'display_name']
        if not all(key in data for key in required_fields):
            logger.warning(f"缺少必需字段: {data.get('id', '未知ID')}")
            return False

        # 字段类型检查
        if not isinstance(data['display_name'], list):
            logger.warning(f"display_name应为列表类型: {data['id']}")
            return False

        # ID格式检查
        if not data['id'].startswith('C_'):
            logger.warning(f"疑似无效课程ID格式: {data['id']}")
            return False

        return True

    def _print_summary(self, stats):
        """输出统计报告"""
        self.stdout.write("\n\n" + "=" * 50)
        self.stdout.write("导入结果摘要：")
        self.stdout.write("-" * 50)
        self.stdout.write(f"总处理条目：{stats['processed']}")
        self.stdout.write(self.style.SUCCESS(f"成功导入：{stats['success']}"))
        self.stdout.write(self.style.WARNING(f"无效数据：{stats['invalid_data']}"))
        self.stdout.write(self.style.WARNING(f"缺失课程：{stats['missing_course']}"))
        self.stdout.write(self.style.ERROR(f"错误数量：{stats['errors']}"))

        if stats['processed'] > 0:
            success_rate = stats['success'] / stats['processed']
            self.stdout.write("-" * 50)
            self.stdout.write(f"成功率：{success_rate:.1%}")
        self.stdout.write("=" * 50 + "\n")


if __name__ == "__main__":
    # 用于直接调试（在Django环境外不要使用）
    import django

    django.setup()
    Command().handle()