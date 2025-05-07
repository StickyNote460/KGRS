# recommender/kg/transE.py
import os
import sys
import django
import torch
import torch.nn as nn
import numpy as np
import time
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

# 设置项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

# 初始化Django环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "KGRS.settings")
django.setup()

from recommender.kg.transE_data import RELATION_TYPES


class TransE(nn.Module):
    def __init__(self, num_entities, num_relations, dim=128, margin=3.0):
        super().__init__()
        self.ent_emb = nn.Embedding(num_entities, dim)
        self.rel_emb = nn.Embedding(num_relations, dim)
        nn.init.xavier_uniform_(self.ent_emb.weight)
        nn.init.xavier_uniform_(self.rel_emb.weight)
        self.margin = margin

    def forward(self, pos_h, pos_r, pos_t, neg_h, neg_t):
        # 调试输出
        print(f"调试 - 正样本关系索引: {pos_r[:5].tolist()}")  # 打印前5个样本的关系索引
        print(f"调试 - 负样本关系索引: {neg_t[:5].tolist()}")

        pos_emb = self.ent_emb(pos_h) + self.rel_emb(pos_r) - self.ent_emb(pos_t)
        pos_score = torch.norm(pos_emb, p=1, dim=1)

        neg_emb = self.ent_emb(neg_h) + self.rel_emb(pos_r) - self.ent_emb(neg_t)
        neg_score = torch.norm(neg_emb, p=1, dim=1)

        return torch.mean(torch.relu(pos_score - neg_score + self.margin))


class KGDataset(Dataset):
    def __init__(self, triples_file):
        self.triples = np.loadtxt(triples_file, dtype=np.int32)

        # 严格验证
        max_rel = np.max(self.triples[:, 2])
        if max_rel >= len(RELATION_TYPES):
            raise ValueError(f"数据文件损坏！检测到关系索引 {max_rel}，最大允许值 {len(RELATION_TYPES) - 1}")

        # 调试输出
        print("\n🔍 数据抽样检查:")
        sample_indices = np.random.choice(len(self.triples), 5, replace=False)
        for idx in sample_indices:
            h, t, r = self.triples[idx]
            print(f"样本 {idx}: 头实体={h}, 尾实体={t}, 关系={r}")

        self.entities = np.unique(np.concatenate(
            [self.triples[:, 0], self.triples[:, 1]]
        ))

    def __len__(self):
        return len(self.triples)

    def __getitem__(self, idx):
        h, t, r = self.triples[idx]
        # 确保负样本不改变关系索引
        if np.random.rand() < 0.5:
            neg_h = np.random.choice(self.entities)
            return torch.LongTensor([h, t, r]), torch.LongTensor([neg_h, t, r])
        else:
            neg_t = np.random.choice(self.entities)
            return torch.LongTensor([h, t, r]), torch.LongTensor([h, neg_t, r])


def train_transE():
    config = {
        'batch_size': 4096,
        'dim': 128,
        'lr': 0.01,
        'epochs': 100,
        'margin': 3.0
    }

    # 加载实体映射
    entity_dict = np.load('entity2id.npy', allow_pickle=True).item()
    entity_count = len(entity_dict)
    print(f"📊 实体总数: {entity_count}")

    # 初始化模型
    model = TransE(
        num_entities=entity_count,
        num_relations=len(RELATION_TYPES),
        dim=config['dim'],
        margin=config['margin']
    )

    # 数据加载
    print("\n🔍 加载训练数据...")
    try:
        dataset = KGDataset('transE_train.txt')
        loader = DataLoader(dataset, batch_size=config['batch_size'], shuffle=True)
        print(f"✅ 有效三元组数量: {len(dataset):,}")
    except Exception as e:
        print(f"❌ 数据加载失败: {str(e)}")
        return

    # 优化器
    opt = torch.optim.Adagrad(model.parameters(), lr=config['lr'])

    # 训练准备
    start_time = time.time()
    print(f"\n🏁 开始训练（共 {config['epochs']} 轮）")

    with tqdm(total=config['epochs'], desc="🌌 总进度", unit="epoch") as pbar_total:
        for epoch in range(config['epochs']):
            epoch_start = time.time()
            total_loss = 0

            with tqdm(loader, desc=f"📅 Epoch {epoch + 1}", unit="batch", leave=False) as pbar_batch:
                for batch_idx, (pos, neg) in enumerate(pbar_batch):
                    # 最终检查（打印第一个错误样本）
                    invalid_mask = pos[:, 2] >= len(RELATION_TYPES)
                    if torch.any(invalid_mask):
                        invalid_idx = torch.where(invalid_mask)[0][0].item()
                        print(f"\n💥 异常正样本数据: {pos[invalid_idx].tolist()}")
                        raise ValueError("关系索引越界")

                    loss = model(*pos.T[:3], neg[:, 0], neg[:, 2])

                    opt.zero_grad()
                    loss.backward()
                    opt.step()

                    total_loss += loss.item()
                    pbar_batch.set_postfix({
                        'loss': f"{loss.item():.3f}",
                        'processed': f"{(batch_idx + 1) * config['batch_size']}/{len(dataset)}"
                    })

            avg_loss = total_loss / len(loader)
            epoch_time = time.time() - epoch_start
            pbar_total.update(1)
            pbar_total.set_postfix({
                'loss': f"{avg_loss:.3f}",
                'time/epoch': f"{epoch_time:.1f}s"
            })

    # 保存结果
    torch.save(model.ent_emb.weight.data.numpy(), 'entity_emb_final.npy')
    print(f"\n🎉 训练完成！总耗时: {(time.time() - start_time) / 60:.1f} 分钟")


if __name__ == '__main__':
    train_transE()