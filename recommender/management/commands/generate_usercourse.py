import json
import csv
from pathlib import Path

# 定义文件路径
base_dir = Path(__file__).resolve().parent.parent.parent.parent
user_json_path = base_dir / "data/raw/user.json"
user_course_json_path = base_dir / "data/raw/user-course.json"
output_csv_path = base_dir / "data/processed/user-course.csv"

# 确保输出目录存在
output_csv_path.parent.mkdir(parents=True, exist_ok=True)

# 读取 user.json，构建用户信息字典
users = {}
with open(user_json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
    for user in data:
        user_id = user['id']
        users[user_id] = {
            'course_order': user.get('course_order', []),
            'enroll_time': user.get('enroll_time', [])
        }

# 读取 user-course.json，并生成 user-course.csv
with open(user_course_json_path, 'r', encoding='utf-8') as infile, \
     open(output_csv_path, 'w', encoding='utf-8', newline='') as outfile:

    reader = csv.reader(infile, delimiter='\t')
    writer = csv.writer(outfile)

    # 写入CSV标题
    writer.writerow(['enroll_time', 'order', 'course_id', 'user_id'])

    # 处理每一行数据
    for row in reader:
        user_id, course_id = row
        if user_id in users:
            user_data = users[user_id]
            # 找到对应的注册时间和顺序
            try:
                idx = user_data['course_order'].index(course_id)
                enroll_time = user_data['enroll_time'][idx] if idx < len(user_data['enroll_time']) else "无注册时间"
                order = idx + 1  # 顺序从1开始
            except ValueError:
                enroll_time = "无注册时间"
                order = "无顺序"

            writer.writerow([enroll_time, order, course_id, user_id])
        else:
            writer.writerow(["无注册时间", "无顺序", course_id, user_id])

print(f"处理完成，结果已保存到 {output_csv_path}")