import json
import csv
from pathlib import Path

# 定义文件路径
base_dir = Path(__file__).resolve().parent.parent.parent.parent
course_json_path = base_dir / "data/raw/course.json"
output_csv_path = base_dir / "data/processed/course.csv"

# 读取 course.json 并提取所需字段
courses = []
with open(course_json_path, 'r', encoding='utf-8') as f:
    for item in json.load(f):
        course_id = item.get("id", "无ID")
        name = item.get("name", "无名称")
        prerequisites = item.get("prerequisites", "无先修要求")
        about = item.get("about", "无简介")
        courses.append({
            'id': course_id,
            'name': name,
            'prerequisites': prerequisites,
            'about': about
        })

# 将提取的字段写入CSV
with open(output_csv_path, 'w', encoding='utf-8', newline='') as csvfile:
    fieldnames = ['id', 'name', 'prerequisites', 'about']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for course in courses:
        writer.writerow(course)

print(f"处理完成，结果已保存到 {output_csv_path}")