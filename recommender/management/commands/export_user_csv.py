# KGRS/recommender/management/commands/export_user_csv.py
import json
import csv
import logging
from django.core.management.base import BaseCommand
from tqdm import tqdm
from pathlib import Path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "从JSON数组文件生成用户学习风格CSV报告（修复版）"

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='启用调试模式（显示详细日志）'
        )
        parser.add_argument(
            '--db-first',
            action='store_true',
            help='数据库数据优先（当冲突时覆盖文件数据）'
        )

    def handle(self, *args, **options):
        try:
            self._setup(options)
            self._validate_paths()
            self._process_data()
            logger.info(f"CSV文件生成成功：{self.output_path}")
        except json.JSONDecodeError as e:
            logger.critical(f"JSON解析失败：{e.doc[:50]}...（位置：{e.pos}）")
        except ValueError as e:
            logger.critical(f"数据结构错误：{str(e)}")
        except Exception as e:
            logger.critical(f"处理失败: {str(e)}", exc_info=options['debug'])
            raise

    def _setup(self, options):
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.input_path = base_dir / "data/raw/user.json"
        self.output_dir = base_dir / "data/processed"
        self.output_path = self.output_dir / "user_ls.csv"

        log_level = logging.DEBUG if options['debug'] else logging.INFO
        logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=log_level
        )

        self.db_first = options['db_first']
        logger.debug(f"配置完成：数据库优先模式={self.db_first}")

    def _validate_paths(self):
        if not self.input_path.exists():
            raise FileNotFoundError(f"输入文件不存在：{self.input_path}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("路径验证通过")

    def _parse_learning_style(self, style_data):
        """统一解析学习风格为字典格式"""
        if isinstance(style_data, dict):
            return style_data
        elif isinstance(style_data, str):
            try:
                return json.loads(style_data)
            except json.JSONDecodeError:
                logger.warning("学习风格字符串解析失败，返回空字典")
                return {}
        else:
            logger.warning(f"未知的学习风格格式：{type(style_data)}")
            return {}

    def _process_data(self):
        """处理JSON数组并生成CSV"""
        from recommender.models import User

        # 加载数据库数据
        logger.info("正在加载数据库用户数据...")
        db_style_map = {}
        try:
            for u in User.objects.only('id', 'learning_style').iterator():
                db_style_map[str(u.id)] = self._parse_learning_style(u.learning_style)
            logger.info(f"已加载 {len(db_style_map)} 条数据库记录")
        except Exception as e:
            logger.error(f"数据库查询失败: {str(e)}")
            raise

        with open(self.input_path, 'r', encoding='utf-8') as f_in:
            try:
                users = json.load(f_in)
                if not isinstance(users, list):
                    raise ValueError("根元素必须是JSON数组")

                total_users = len(users)
                logger.info(f"发现 {total_users} 个用户记录")

                with open(self.output_path, 'w', newline='', encoding='utf-8') as f_out:
                    writer = csv.writer(f_out)
                    writer.writerow(['id', 'name', 'learning_style'])

                    success_count = 0
                    error_count = 0

                    with tqdm(users, desc="处理用户", unit="用户") as pbar:
                        for user in pbar:
                            try:
                                # 数据验证
                                if 'id' not in user or 'name' not in user:
                                    raise ValueError(f"缺少必要字段，数据：{user}")

                                user_id = str(user['id'])  # 统一ID为字符串格式
                                user_name = user['name']

                                # 合并学习风格
                                file_style = self._parse_learning_style(
                                    user.get('learning_style', {})
                                )
                                db_style = db_style_map.get(user_id, {})

                                if self.db_first:
                                    merged_style = {**file_style, **db_style}
                                else:
                                    merged_style = {**db_style, **file_style}

                                # 写入CSV
                                writer.writerow([
                                    user_id,
                                    user_name,
                                    json.dumps(merged_style, ensure_ascii=False)
                                    if merged_style else ""
                                ])
                                success_count += 1
                            except Exception as e:
                                error_count += 1
                                logger.warning(
                                    f"用户处理失败（ID: {user.get('id', '未知')}）: {str(e)}\n"
                                    f"完整数据：{json.dumps(user, ensure_ascii=False)[:200]}"
                                )
                                pbar.set_postfix({'成功': success_count, '失败': error_count})

                logger.info(f"处理完成：成功 {success_count} 条，失败 {error_count} 条")

            except json.JSONDecodeError as e:
                logger.error("JSON格式错误，请检查：")
                logger.error(f"错误位置：{e.pos}，上下文：{e.doc[e.pos - 30:e.pos + 30]}")
                raise


if __name__ == "__main__":
    Command().run_from_argv(['manage.py', 'export_user_csv'])