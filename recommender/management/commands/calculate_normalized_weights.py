# recommender/management/commands/calculate_normalized_weights.py
import numpy as np
import pickle
import hashlib
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import logging
import time

from recommender.models import Course, Concept, CourseConcept

# 配置日志记录
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class EmbeddingCache:
    """BERT嵌入缓存管理器"""

    def __init__(self, cache_dir=".embedding_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, text):
        """生成文本的MD5哈希作为缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def load_embeddings(self, texts):
        """批量加载缓存"""
        cached = {}
        missing_indices = []
        for idx, text in enumerate(texts):
            key = self._get_cache_key(text)
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    cached[idx] = pickle.load(f)
            else:
                missing_indices.append(idx)
        return cached, missing_indices

    def save_embeddings(self, texts, embeddings, indices):
        """批量保存缓存"""
        for i, idx in enumerate(indices):
            key = self._get_cache_key(texts[idx])
            cache_file = self.cache_dir / f"{key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(embeddings[i], f)


class WeightOptimizer:
    """动态权重调整器"""

    def __init__(self, initial_alpha=0.4, initial_beta=0.3, initial_gamma=0.3):
        self.alpha = initial_alpha
        self.beta = initial_beta
        self.gamma = initial_gamma
        self.history = []

    def adjust_weights(self, evaluation_metric):
        """示例回调函数（需根据实际评估指标实现）"""
        # 此处应包含推荐效果评估逻辑
        # 示例：根据历史表现调整权重
        if len(self.history) >= 2 and evaluation_metric < np.mean(self.history[-2:]):
            self.alpha *= 0.9
            self.beta *= 1.1
            self.gamma *= 1.0
            logger.info(f"Adjusting weights: alpha={self.alpha:.2f}, beta={self.beta:.2f}, gamma={self.gamma:.2f}")

        self.history.append(evaluation_metric)
        return self.alpha, self.beta, self.gamma


class Command(BaseCommand):
    help = '''Calculate normalized weights with advanced features'''

    def add_arguments(self, parser):
        parser.add_argument('--alpha', type=float, default=0.4,
                            help='Initial weight for structured feature')
        parser.add_argument('--beta', type=float, default=0.3,
                            help='Initial weight for video similarity')
        parser.add_argument('--gamma', type=float, default=0.3,
                            help='Initial weight for explanation similarity')
        parser.add_argument('--tune', action='store_true',
                            help='Enable auto-tuning mode')
        parser.add_argument('--cache', action='store_true',
                            help='Enable embedding caching')
        parser.add_argument('--no-cache', dest='cache', action='store_false',
                            help='Disable embedding caching')
        parser.set_defaults(cache=True)

    def _validate_weights(self, alpha, beta, gamma):
        """权重参数校验"""
        if not np.isclose(alpha + beta + gamma, 1.0, atol=0.001):
            raise ValueError(f"权重之和必须为1.0 (当前: {alpha + beta + gamma:.2f})")

    def handle(self, *args, **options):
        try:
            # 初始化系统
            self._validate_weights(options['alpha'], options['beta'], options['gamma'])
            optimizer = WeightOptimizer(options['alpha'], options['beta'], options['gamma'])
            cache = EmbeddingCache() if options['cache'] else None

            # 数据加载阶段
            logger.info("Stage 1/5: 加载数据...")
            with self._log_time("数据加载"):
                courses = list(Course.objects.prefetch_related('concepts').all())
                concepts = list(Concept.objects.all())
                all_cc = list(CourseConcept.objects.select_related('course', 'concept').all())

            # 文本预处理
            logger.info("Stage 2/5: 文本预处理...")
            with self._log_time("文本预处理"):
                course_data, concept_data = self._preprocess_texts(courses, concepts)

            # 特征计算
            logger.info("Stage 3/5: 特征计算...")
            with self._log_time("特征计算"):
                tfidf_features = self._calculate_tfidf(course_data, concept_data)
                bert_features = self._calculate_bert(
                    course_data, concept_data,
                    cache_enabled=options['cache'],
                    cache_manager=cache
                )

            # 权重计算与归一化
            logger.info("Stage 4/5: 权重计算...")
            with self._log_time("权重计算"):
                self._calculate_weights(
                    all_cc, courses, concepts,
                    tfidf_features, bert_features,
                    optimizer, options
                )

            # 特征监控
            logger.info("Stage 5/5: 特征监控...")
            self._monitor_features(all_cc)

            # 动态调整演示
            if options['tune']:
                logger.info("执行动态调整...")
                # 此处应接入实际评估系统
                optimizer.adjust_weights(0.75)  # 示例评估值

        except Exception as e:
            logger.error(f"处理失败: {str(e)}")
            raise e

    def _preprocess_texts(self, courses, concepts):
        """文本预处理"""
        course_video_map = {}
        course_fulltext_map = {}
        for course in tqdm(courses, desc="课程文本处理"):
            video_text = ' '.join(course.video_name) or '无视频'
            course_video_map[course.id] = video_text
            course_fulltext_map[course.id] = f"{course.about} {video_text}" or '无简介'

        concept_video_map = {}
        concept_explanation_map = {}
        for concept in tqdm(concepts, desc="概念文本处理"):
            concept_video_map[concept.id] = f"{concept.name} {concept.explanation}" or '无解释'
            concept_explanation_map[concept.id] = concept.explanation or '无解释'

        return (course_video_map, course_fulltext_map), (concept_video_map, concept_explanation_map)

    def _calculate_tfidf(self, course_data, concept_data):
        """计算TF-IDF特征"""
        course_video_map, _ = course_data
        concept_video_map, _ = concept_data

        corpus = list(course_video_map.values()) + list(concept_video_map.values())
        vectorizer = TfidfVectorizer(min_df=2, max_features=5000)
        matrix = vectorizer.fit_transform(corpus)

        return {
            'course': matrix[:len(course_video_map)],
            'concept': matrix[len(course_video_map):],
            'vectorizer': vectorizer
        }

    def _calculate_bert(self, course_data, concept_data, cache_enabled, cache_manager):
        """计算BERT嵌入"""
        _, course_fulltext_map = course_data
        _, concept_explanation_map = concept_data

        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # 课程嵌入
        course_texts = [course_fulltext_map[c.id] for c in Course.objects.all()]
        course_embeds = self._batch_bert(
            model, course_texts,
            "课程嵌入计算", cache_enabled, cache_manager
        )

        # 概念嵌入
        concept_texts = [concept_explanation_map[c.id] for c in Concept.objects.all()]
        concept_embeds = self._batch_bert(
            model, concept_texts,
            "概念嵌入计算", cache_enabled, cache_manager
        )

        return {
            'course': {c.id: e for c, e in zip(Course.objects.all(), course_embeds)},
            'concept': {c.id: e for c, e in zip(Concept.objects.all(), concept_embeds)}
        }

    def _batch_bert(self, model, texts, desc, use_cache, cache_manager):
        """批量处理BERT嵌入"""
        try:
            if use_cache and cache_manager:
                cached, missing = cache_manager.load_embeddings(texts)
                logger.info(f"缓存命中率: {len(cached)}/{len(texts)}")

                # 处理未命中部分
                if missing:
                    logger.info(f"计算新嵌入: {len(missing)}条")
                    new_embeds = model.encode(
                        [texts[i] for i in missing],
                        batch_size=64,
                        show_progress_bar=True,
                        convert_to_numpy=True
                    )
                    cache_manager.save_embeddings(texts, new_embeds, missing)

                # 合并结果
                embeds = np.zeros((len(texts), 384))
                for idx in range(len(texts)):
                    if idx in cached:
                        embeds[idx] = cached[idx]
                    else:
                        embeds[idx] = new_embeds[missing.index(idx)]
                return embeds
            else:
                return model.encode(texts, batch_size=64, show_progress_bar=True)
        except Exception as e:
            logger.error(f"BERT处理失败: {str(e)}")
            raise

    def _calculate_weights(self, all_cc, courses, concepts, tfidf, bert, optimizer, options):
        """核心权重计算逻辑"""
        course_cc_map = {}
        for cc in all_cc:
            course_cc_map.setdefault(cc.course.id, []).append(cc)

        try:
            with transaction.atomic():
                for course_id, cc_list in tqdm(course_cc_map.items(), desc="课程处理"):
                    course = next(c for c in courses if c.id == course_id)

                    weights = []
                    for cc in cc_list:
                        # 结构化特征
                        struct = cc.concept.topsis_score

                        # 视频相似度
                        c_vec = tfidf['course'][courses.index(course)]
                        k_vec = tfidf['concept'][concepts.index(cc.concept)]
                        video_sim = cosine_similarity(c_vec, k_vec)[0, 0]

                        # 解释相似度
                        c_embed = bert['course'][course_id].reshape(1, -1)
                        k_embed = bert['concept'][cc.concept.id].reshape(1, -1)
                        explain_sim = cosine_similarity(c_embed, k_embed)[0, 0]

                        # 动态权重调整
                        if options['tune']:
                            a, b, g = optimizer.adjust_weights(None)  # 需传入真实评估指标
                        else:
                            a, b, g = optimizer.alpha, optimizer.beta, optimizer.gamma

                        combined = a * struct + b * video_sim + g * explain_sim
                        weights.append(combined)

                    # Softmax归一化
                    weights = self._safe_softmax(weights)

                    # 批量更新
                    for cc, w in zip(cc_list, weights):
                        cc.normalized_weight = w
                    CourseConcept.objects.bulk_update(cc_list, ['normalized_weight'])
        except IntegrityError as e:
            logger.error(f"数据库更新失败: {str(e)}")
            raise

    def _safe_softmax(self, x):
        """数值稳定的Softmax"""
        x = np.array(x)
        x = x - np.max(x)
        e_x = np.exp(x)
        return e_x / e_x.sum()

    def _monitor_features(self, relations):
        """特征监控报告"""
        weights = [cc.normalized_weight for cc in relations]
        stats = {
            'min': np.min(weights),
            'max': np.max(weights),
            'mean': np.mean(weights),
            'std': np.std(weights),
            'hist': np.histogram(weights, bins=10)
        }

        logger.info("\n特征分布报告:")
        logger.info(f"最小值: {stats['min']:.4f}")
        logger.info(f"最大值: {stats['max']:.4f}")
        logger.info(f"平均值: {stats['mean']:.4f} ± {stats['std']:.4f}")
        logger.info("分布直方图:")
        for i in range(10):
            logger.info(f"[{stats['hist'][1][i]:.2f}-{stats['hist'][1][i + 1]:.2f}]: {stats['hist'][0][i]}")

    class _log_time:
        """执行时间记录上下文管理器"""

        def __init__(self, task_name):
            self.task_name = task_name

        def __enter__(self):
            self.start = time.time()
            logger.info(f"开始 {self.task_name}...")

        def __exit__(self, *args):
            duration = time.time() - self.start
            logger.info(f"完成 {self.task_name}，耗时 {duration:.1f}秒")