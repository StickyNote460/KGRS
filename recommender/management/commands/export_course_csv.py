# KGRS/recommender/management/commands/export_course_csv.py
import json
import csv
import logging
from pathlib import Path
from django.core.management.base import BaseCommand
from tqdm import tqdm
from bs4 import BeautifulSoup  # 需要安装：pip install beautifulsoup4

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "将课程数据导出为CSV文件（新增difficulty/popularity字段）"

    # 路径配置
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    JSON_PATH = BASE_DIR / "data" / "raw" / "course.json"
    CSV_PATH = BASE_DIR / "data" / "processed" / "video_names.csv"

    def handle(self, *args, **kwargs):
        """主处理逻辑"""
        try:
            # 步骤1：读取并验证JSON数据
            if not self.JSON_PATH.exists():
                raise FileNotFoundError(f"JSON文件不存在: {self.JSON_PATH}")

            with open(self.JSON_PATH, 'r', encoding='utf-8') as f:
                courses_data = json.load(f)

            # 步骤2：创建CSV文件并写入数据
            self.CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

            with open(self.CSV_PATH, 'w', encoding='utf-8-sig', newline='') as csvfile:
                fieldnames = [
                    'id', 'name', 'prerequisites', 'about',
                    'video_name', 'difficulty', 'popularity'  # 新增字段
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                # 进度条设置
                progress = tqdm(courses_data, desc="处理课程", unit="条")

                for course_data in progress:
                    try:
                        processed = self._process_data(course_data)
                        writer.writerow(processed)
                        progress.set_postfix({'状态': '成功'})
                    except Exception as e:
                        logger.error(f"处理失败: {str(e)}", exc_info=True)
                        progress.set_postfix({'状态': '错误'})

            self.stdout.write(self.style.SUCCESS(f"\n成功导出CSV文件到: {self.CSV_PATH}"))

        except Exception as e:
            logger.error(f"全局错误: {str(e)}", exc_info=True)
            raise

    def _process_data(self, data):
        """处理单个课程数据（新增固定字段）"""
        # 必需字段校验
        required_fields = ['id', 'name', 'prerequisites', 'about', 'display_name']
        if not all(key in data for key in required_fields):
            raise ValueError("缺少必需字段")

        # 处理about字段
        about_clean = self._clean_about(data['about'])

        # # 处理video_name：转换列表为分号分隔字符串
        # video_str = ';'.join([
        #     name.strip()
        #     for name in data['display_name']
        #     if isinstance(name, str) and name.strip()
        # ])
        # 新代码：生成JSON数组字符串
        video_list = [
            name.strip()
            for name in data['display_name']
            if isinstance(name, str) and name.strip()
        ]
        video_json = json.dumps(video_list, ensure_ascii=False)  # 转换为JSON数组

        return {
            'id': data['id'],
            'name': data['name'],
            'prerequisites': data['prerequisites'],
            'about': about_clean,
            'video_name': video_json,
            'difficulty': 1,  # 固定值
            'popularity': 0  # 固定值
        }

    def _clean_about(self, raw_text):
        """清理about字段（保留换行效果）"""
        try:
            soup = BeautifulSoup(raw_text, 'html.parser')
            text = soup.get_text(separator='\n')  # 保留换行
            return '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
        except Exception as e:
            logger.warning(f"清理about字段失败: {str(e)}")
            return raw_text


if __name__ == "__main__":
    import django

    django.setup()
    Command().handle()