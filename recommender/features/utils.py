import hashlib
import pickle
from pathlib import Path
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """BERT嵌入缓存管理器（完整实现）"""

    def __init__(self, cache_dir: str = ".embedding_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, text: str) -> str:
        """生成文本的MD5哈希作为缓存键"""
        return hashlib.md5(text.strip().encode('utf-8')).hexdigest()

    def load_embeddings(self, texts: list) -> tuple[dict, list]:
        """批量加载缓存"""
        cached = {}
        missing_indices = []

        for idx, text in enumerate(texts):
            if not text.strip():
                continue

            key = self._get_cache_key(text)
            cache_file = self.cache_dir / f"{key}.pkl"

            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        cached[idx] = pickle.load(f)
                except Exception as e:
                    logger.warning(f"加载缓存失败 {cache_file}: {str(e)}")
                    missing_indices.append(idx)
            else:
                missing_indices.append(idx)

        return cached, missing_indices

    def save_embeddings(self, texts: list, embeddings: np.ndarray, indices: list):
        """批量保存缓存"""
        for i, idx in enumerate(indices):
            text = texts[idx]
            if not text.strip():
                continue

            key = self._get_cache_key(text)
            cache_file = self.cache_dir / f"{key}.pkl"

            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(embeddings[i], f, protocol=4)
            except Exception as e:
                logger.error(f"保存缓存失败 {cache_file}: {str(e)}")


class WeightOptimizer:
    """动态权重调整器（完整实现）"""

    def __init__(self,
                 initial_alpha: float = 0.4,
                 initial_beta: float = 0.3,
                 initial_gamma: float = 0.3,
                 decay_rate: float = 0.9,
                 boost_rate: float = 1.1):
        self.alpha = initial_alpha
        self.beta = initial_beta
        self.gamma = initial_gamma
        self.history = []
        self.decay_rate = decay_rate
        self.boost_rate = boost_rate
        self.min_weight = 0.1
        self.max_weight = 0.8

    def _normalize_weights(self):
        """权重归一化处理"""
        total = self.alpha + self.beta + self.gamma
        self.alpha /= total
        self.beta /= total
        self.gamma /= total

        # 应用边界限制
        self.alpha = np.clip(self.alpha, self.min_weight, self.max_weight)
        self.beta = np.clip(self.beta, self.min_weight, self.max_weight)
        self.gamma = np.clip(self.gamma, self.min_weight, self.max_weight)
        self._normalize_weights()

    def adjust_weights(self, evaluation_metric: Optional[float] = None) -> tuple[float, float, float]:
        """动态调整权重"""
        if evaluation_metric is not None and len(self.history) >= 3:
            last_avg = np.mean(self.history[-3:])
            if evaluation_metric < last_avg:
                # 衰减结构化特征权重
                self.alpha *= self.decay_rate
                # 增强语义特征权重
                self.beta *= self.boost_rate
                self.gamma *= self.boost_rate
                logger.info("触发权重衰减策略")

        self._normalize_weights()
        self.history.append(evaluation_metric or 0.0)
        return self.alpha, self.beta, self.gamma

    def get_weights(self) -> tuple[float, float, float]:
        """获取当前权重"""
        return self.alpha, self.beta, self.gamma