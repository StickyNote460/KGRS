import json
import csv
from pathlib import Path

# 定义文件路径
base_dir = Path(__file__).resolve().parent.parent.parent.parent
concept_json_path = base_dir / "data/raw/concept.json"
concept_field_json_path = base_dir / "data/raw/concept-field.json"
output_csv_path = base_dir / "data/processed/concept.csv"

# 读取 concept.json 并提取所需字段
concepts = []
with open(concept_json_path, 'r', encoding='utf-8') as f:
    for item in json.load(f):
        concept_id = item.get("id", "无ID")
        name = item.get("name", "无名称")
        explanation = item.get("explanation", "无相应简介")
        concepts.append({
            "id": concept_id,
            "name": name,
            "explanation": explanation
        })

# 读取 concept-field.json 并建立概念ID到领域ID的映射
concept_to_field = {}
with open(concept_field_json_path, 'r', encoding='utf-8') as f:
    for line in f:
        # 假设每行是制表符分隔的 "概念ID\t领域ID"
        if "\t" in line:
            concept_id, field_id = line.strip().split("\t")
            concept_to_field[concept_id] = field_id
        else:
            # 处理可能的空行或格式错误
            continue

# 将领域ID作为field字段写入CSV
with open(output_csv_path, 'w', encoding='utf-8', newline='') as csvfile:
    fieldnames = ['id', 'name', 'explanation', 'field']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for concept in concepts:
        concept_id = concept['id']
        # 获取对应的领域ID，如果没有则填充"无领域"
        field = concept_to_field.get(concept_id, "无领域")
        writer.writerow({
            'id': concept_id,
            'name': concept['name'],
            'explanation': concept['explanation'],
            'field': field
        })

print(f"处理完成，结果已保存到 {output_csv_path}")