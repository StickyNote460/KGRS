import logging
from typing import Optional
#from typing_extensions import Optional

import numpy as np
from tqdm import tqdm
from django.db import models, transaction
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from recommender.models import Course, CourseConcept, Concept
from recommender.features.utils import EmbeddingCache, WeightOptimizer

logger = logging.getLogger(__name__)


def calculate_course_difficulty(batch_size: int = 500):
    """计算课程难度（完整实现）"""
    try:
        logger.info("开始计算课程难度...")

        courses = Course.objects.prefetch_related(
            models.Prefetch('concepts', queryset=Concept.objects.only('depth'))
        ).all()

        updates = []
        for course in tqdm(courses, desc="处理课程"):
            depths = [c.depth for c in course.concepts.all()]
            avg_depth = sum(depths) / len(depths) if depths else 1.0
            updates.append((course.id, avg_depth))

        # 批量更新
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            Course.objects.bulk_update(
                [Course(id=id, difficulty=difficulty) for id, difficulty in batch],
                ['difficulty']
            )

        logger.info("课程难度计算完成")

    except Exception as e:
        logger.error(f"课程难度计算失败: {str(e)}")
        raise


def calculate_normalized_weights(alpha: float = 0.4, beta: float = 0.3, gamma: float = 0.3,
                                 cache: bool = True, batch_size: int = 100):
    """课程-概念归一化权重计算（完整实现）"""
    try:
        logger.info("开始计算归一化权重...")

        # 初始化组件
        cache_manager = EmbeddingCache() if cache else None
        optimizer = WeightOptimizer(alpha, beta, gamma)
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # 获取所有课程概念关系
        all_cc = list(CourseConcept.objects.select_related(
            'course', 'concept').prefetch_related('course__concepts'))

        # 文本预处理
        course_texts = []
        concept_texts = []
        for cc in all_cc:
            course_text = f"{cc.course.about} {' '.join(cc.course.video_name)}".strip() or "无内容"
            concept_text = f"{cc.concept.name} {cc.concept.explanation}".strip() or "无内容"
            course_texts.append(course_text)
            concept_texts.append(concept_text)

        # TF-IDF计算
        vectorizer = TfidfVectorizer(min_df=2, max_features=5000)
        tfidf_matrix = vectorizer.fit_transform(course_texts + concept_texts)
        course_tfidf = tfidf_matrix[:len(all_cc)]
        concept_tfidf = tfidf_matrix[len(all_cc):]

        # BERT嵌入计算
        course_embeddings = _batch_bert_embed(model, course_texts, cache_manager, "课程")
        concept_embeddings = _batch_bert_embed(model, concept_texts, cache_manager, "概念")

        # 权重计算
        with transaction.atomic():
            for i in tqdm(range(0, len(all_cc), batch_size), desc="处理关系"):
                batch_cc = all_cc[i:i + batch_size]

                updates = []
                for j, cc in enumerate(batch_cc):
                    idx = i + j

                    # 结构化特征
                    struct = cc.concept.topsis_score

                    # TF-IDF相似度
                    tfidf_sim = cosine_similarity(
                        course_tfidf[idx],
                        concept_tfidf[idx]
                    )[0][0]

                    # BERT相似度
                    bert_sim = cosine_similarity(
                        course_embeddings[idx].reshape(1, -1),
                        concept_embeddings[idx].reshape(1, -1)
                    )[0][0]

                    # 动态调整权重
                    a, b, g = optimizer.get_weights()
                    combined = a * struct + b * tfidf_sim + g * bert_sim
                    cc.normalized_weight = combined
                    updates.append(cc)

                # Softmax归一化
                weights = [cc.normalized_weight for cc in updates]
                softmax_weights = _safe_softmax(weights)
                for cc, w in zip(updates, softmax_weights):
                    cc.normalized_weight = w

                CourseConcept.objects.bulk_update(updates, ['normalized_weight'])

        logger.info("归一化权重计算完成")

    except Exception as e:
        logger.error(f"归一化权重计算失败: {str(e)}")
        raise


def _batch_bert_embed(model, texts: list, cache_manager: Optional[EmbeddingCache], desc: str) -> np.ndarray:
    """批量计算BERT嵌入"""
    try:
        embeddings = np.zeros((len(texts), 384))

        if cache_manager:
            cached, missing = cache_manager.load_embeddings(texts)
            logger.info(f"{desc}缓存命中率: {len(cached)}/{len(texts)}")

            if missing:
                logger.info(f"计算新{desc}嵌入: {len(missing)}条")
                new_embeds = model.encode(
                    [texts[i] for i in missing],
                    batch_size=64,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                cache_manager.save_embeddings(texts, new_embeds, missing)

                for i, idx in enumerate(missing):
                    embeddings[idx] = new_embeds[i]

            for idx in cached:
                embeddings[idx] = cached[idx]
        else:
            embeddings = model.encode(texts, batch_size=64, show_progress_bar=False)

        return embeddings
    except Exception as e:
        logger.error(f"BERT嵌入计算失败: {str(e)}")
        raise


def _safe_softmax(x: list) -> np.ndarray:
    """数值稳定的Softmax"""
    x = np.array(x)
    x = x - np.max(x)
    e_x = np.exp(x)
    return e_x / (e_x.sum() + 1e-12)