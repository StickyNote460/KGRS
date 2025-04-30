# recommender/management/commands/generate_field.py
import csv
from pathlib import Path
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Generate field.csv from concept-field.json'

    def handle(self, *args, **kwargs):
        # ===================== 路径配置 =====================
        # 当前脚本绝对路径：KGRS/recommender/management/commands/generate_field.py
        script_path = Path(__file__).resolve()

        # 项目根目录：KGRS/
        base_dir = script_path.parent.parent.parent.parent

        # 输入文件路径：KGRS/data/raw/concept-field.json
        input_path = base_dir / "data" / "raw" / "concept-field.json"

        # 输出文件路径：KGRS/data/processed/field.csv
        output_path = base_dir / "data" / "processed" / "field.csv"

        # ===================== 路径验证 =====================
        self.stdout.write(f"项目根目录：{base_dir}")
        self.stdout.write(f"输入文件路径：{input_path}")
        self.stdout.write(f"输出文件路径：{output_path}")

        if not input_path.exists():
            self.stdout.write(self.style.ERROR(f"错误：输入文件不存在 → {input_path}"))
            return

        # ===================== 数据处理 =====================
        fields = {}
        line_count = 0

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_count += 1
                    line = line.strip()
                    if not line:
                        continue

                    # 分割字段
                    parts = line.split('\t')
                    if len(parts) < 2:
                        self.stdout.write(self.style.WARNING(f"第 {line_count} 行格式错误，跳过"))
                        continue

                    # 提取领域ID
                    field_id = parts[1].strip()

                    # 解析领域名称（取最后一段）
                    try:
                        field_name = field_id.split('_')[-1]
                    except IndexError:
                        self.stdout.write(self.style.WARNING(f"第 {line_count} 行ID格式错误：{field_id}"))
                        continue

                    # 存储唯一记录
                    fields[field_id] = field_name

            self.stdout.write(f"成功解析 {len(fields)} 个领域（总行数：{line_count}）")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"文件读取失败：{str(e)}"))
            return

        # ===================== 写入文件 =====================
        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'name', 'parent'])

                for field_id, name in fields.items():
                    writer.writerow([field_id, name, ''])

            self.stdout.write(self.style.SUCCESS(f"文件已生成 → {output_path}"))
            self.stdout.write(f"文件大小：{output_path.stat().st_size} 字节")

        except PermissionError:
            self.stdout.write(self.style.ERROR("权限拒绝：请关闭已打开的CSV文件"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"文件写入失败：{str(e)}"))