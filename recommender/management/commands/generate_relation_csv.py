import csv
from pathlib import Path

# 定义文件路径和输出路径
base_dir = Path(__file__).resolve().parent.parent.parent.parent
input_dir = base_dir / "data/raw"
output_dir = base_dir / "data/processed"

# 确保输出目录存在
output_dir.mkdir(parents=True, exist_ok=True)

# 定义输入文件和对应的输出文件名
file_mappings = {
    "concept-field.json": "concept-field.csv",
    "course-concept.json": "course-concept.csv",
    "parent-son.json": "parent-son.csv",
    "prerequisite-dependency.json": "prerequisite-dependency.csv"
}

# 处理每个文件
for input_filename, output_filename in file_mappings.items():
    input_path = input_dir / input_filename
    output_path = output_dir / output_filename

    with open(input_path, 'r', encoding='utf-8') as infile, \
            open(output_path, 'w', encoding='utf-8', newline='') as outfile:

        # 假设每行是制表符分隔的键值对
        reader = infile
        writer = csv.writer(outfile)

        # 写入CSV标题（假设没有标题，直接写入数据）
        # 如果需要标题，可以在这里添加 writer.writerow(['source', 'target'])

        for line in reader:
            line = line.strip()
            if line:  # 跳过空行
                try:
                    source, target = line.split('\t')
                    writer.writerow([source, target])
                except ValueError:
                    print(f"警告：无法解析的行: {line}，文件: {input_filename}")
                    continue

print("处理完成，结果已保存到 /data/processed/")

# 定义文件路径
base_dir = Path(__file__).resolve().parent.parent.parent.parent
input_csv_path = base_dir / "data/processed/course-concept.csv"
output_csv_path = base_dir / "data/processed/course-concept-weight.csv"

# 确保输出目录存在
output_csv_path.parent.mkdir(parents=True, exist_ok=True)

# 读取输入 CSV 并添加 weight 列
with open(input_csv_path, 'r', encoding='utf-8') as infile, \
     open(output_csv_path, 'w', encoding='utf-8', newline='') as outfile:

    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    # 处理每一行数据并添加 weight 列
    for row in reader:
        row.append('1')  # 添加 weight 列，值为 1
        writer.writerow(row)

print(f"处理完成，结果已保存到 {output_csv_path}")