import sqlite3
import csv
from pathlib import Path

# 定义文件路径
base_dir = Path(__file__).resolve().parent.parent.parent.parent
csv_file_path = base_dir / "data/processed/user-course.csv"
db_path = base_dir / "db.sqlite3"

# 确保数据库连接和文件路径正确
if not csv_file_path.exists():
    raise FileNotFoundError(f"CSV file not found at {csv_file_path}")

# 连接到 SQLite 数据库
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# 确保外键约束启用
cursor.execute("PRAGMA foreign_keys = ON;")
#
# # 创建表（如果不存在）
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS user_course (
#     user_id TEXT,
#     course_id TEXT,
#     enroll_time TEXT,
#     "order" INTEGER,
#     FOREIGN KEY (user_id) REFERENCES user(id),
#     FOREIGN KEY (course_id) REFERENCES course(id)
# );
# """)

# 读取 CSV 文件并插入数据
with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
    csv_reader = csv.reader(csvfile)
    next(csv_reader)  # 跳过标题行

    for row in csv_reader:
        try:
            enroll_time, order, course_id, user_id = row  # 根据 CSV 列顺序调整变量顺序
            cursor.execute("""
            INSERT INTO user_course (enroll_time, "order", course_id, user_id)
            VALUES (?, ?, ?, ?);
            """, (enroll_time, order, course_id, user_id))
            conn.commit()  # 提交每个插入操作
        except sqlite3.IntegrityError as e:
            print(f"插入失败，跳过此行: {row}，错误信息: {e}")
            conn.rollback()  # 回滚当前事务
        except Exception as e:
            print(f"发生未知错误，跳过此行: {row}，错误信息: {e}")
            conn.rollback()  # 回滚当前事务

# 关闭数据库连接
conn.close()

print("CSV 数据导入完成。")