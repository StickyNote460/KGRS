# update_precourses_v3.py
import re
import logging
from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm
from recommender.models import Course

logger = logging.getLogger(__name__)


class CourseMatcher:
    """增强版课程匹配器"""

    def __init__(self):
        self.all_courses = {c.name: c for c in Course.objects.all()}
        self._build_indexes()

    def _build_indexes(self):
        """构建多级索引"""
        self.exact_match = {name: name for name in self.all_courses}
        self.norm_match = {}
        self.alias_map = {
            '大物': '大学物理',
            '线代': '线性代数',
            '高数': '高等数学',
            # 可在此添加更多别名
        }

        for name in self.all_courses:
            # 标准化名称索引
            norm_name = self._normalize(name)
            if norm_name not in self.norm_match:
                self.norm_match[norm_name] = name

            # 提取名称主干（用于模糊匹配）
            stem = re.sub(r'[^\\u4e00-\\u9fff]', '', name)[:4]
            if stem not in self.norm_match:
                self.norm_match[stem] = name

    @staticmethod
    def _normalize(text: str) -> str:
        """深度标准化文本"""
        return re.sub(r'[^\w\u4e00-\u9fff]', '', text).lower()

    def find_matches(self, query: str, threshold=0.65) -> list:
        """多维度匹配策略"""
        try:
            # 别名优先
            if query in self.alias_map:
                return [self.alias_map[query]]

            # 精确匹配
            if query in self.exact_match:
                return [self.exact_match[query]]

            # 标准化匹配
            norm_query = self._normalize(query)
            if norm_query in self.norm_match:
                return [self.norm_match[norm_query]]

            # 模糊匹配
            matches = []
            for name in self.all_courses:
                ratio = SequenceMatcher(None, norm_query, self._normalize(name)).ratio()
                if ratio >= threshold:
                    matches.append((name, ratio))

            # 按相似度排序
            return [x[0] for x in sorted(matches, key=lambda x: x[1], reverse=True)]
        except Exception as e:
            logger.error(f"匹配查询失败: {query} - {str(e)}")
            return []


class Command(BaseCommand):
    help = '增强版先修课程提取与匹配'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.65,
            help='模糊匹配阈值（默认0.65）'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='批量提交数量'
        )

    def handle(self, *args, **kwargs):
        threshold = kwargs['threshold']
        batch_size = kwargs['batch_size']
        matcher = CourseMatcher()

        with transaction.atomic():
            updates = []
            for course in tqdm(Course.objects.all().iterator(), desc="处理课程"):
                try:
                    # ===== 提取阶段 =====
                    try:
                        candidates = self._extract_candidates(course.prerequisites)
                        course.abstract_pre_courses = candidates if candidates else []
                    except Exception as e:
                        course.abstract_pre_courses = "False"
                        logger.warning(f"课程 {course.id} 提取异常: {str(e)}")

                    # ===== 匹配阶段 =====
                    if course.abstract_pre_courses == "False":
                        course.match_pre_courses = "False"
                    elif not course.abstract_pre_courses:
                        course.match_pre_courses = []
                    else:
                        matched = []
                        for candidate in course.abstract_pre_courses:
                            matches = matcher.find_matches(candidate, threshold)
                            if matches:
                                matched.append(matches[0])
                            else:
                                matched.append(f"{candidate}【系统暂未收录此课程，敬请期待】")

                        # 去重处理（保留顺序）
                        seen = set()
                        course.match_pre_courses = []
                        for item in matched:
                            if item not in seen:
                                course.match_pre_courses.append(item)
                                seen.add(item)

                    updates.append(course)

                    # 批量提交
                    if len(updates) >= batch_size:
                        self._bulk_update(updates)
                        updates = []

                except Exception as e:
                    logger.error(f"处理课程 {course.id} 失败: {str(e)}")
                    continue

            if updates:
                self._bulk_update(updates)

    def _bulk_update(self, courses):
        """优化批量更新"""
        Course.objects.bulk_update(
            courses,
            ['abstract_pre_courses', 'match_pre_courses'],
            batch_size=500
        )

    def _extract_candidates(self, text: str) -> list:
        """增强型候选提取"""
        try:
            if not text:
                return []

            # 预处理流程
            text = text.replace('\r\n', ' ') \
                .replace('\\n', ' ') \
                .strip('，。；、')

            # 模式识别（优先级从高到低）
            patterns = [
                (r'《([^》]+)》', 1),  # 匹配书名号
                (r'先修课程?[:：]\s*([^。]+)', 1),  # 结构化声明
                (r'"(.*?)"', 1),  # 英文引号
                (r'“(.*?)”', 1),  # 中文引号
                (r'([\u4e00-\u9fff]{2,8}（[^）]+）)', 0),  # 带括号的课程名
                (r'([\u4e00-\u9fff]{2,8})', 0)  # 纯中文课程名
            ]

            candidates = []
            for pattern, weight in patterns:
                found = re.findall(pattern, text)
                candidates.extend([(x, weight) for x in found])

            # 权重排序并去重
            sorted_candidates = sorted(
                {x[0] for x in candidates},
                key=lambda x: -max(w for (v, w) in candidates if v == x)
            )

            # 分割复合条目
            split_chars = ['、', ',', ';', '；', '/', '及', '与', '和']
            final_candidates = []
            for item in sorted_candidates:
                for sep in split_chars:
                    item = item.replace(sep, '|')
                final_candidates.extend(
                    [x.strip() for x in item.split('|') if x.strip()]
                )

            # 最终过滤
            return [
                item for item in final_candidates
                if len(item) >= 2
                   and not any(kw in item for kw in ['无', '建议', '基础课'])
            ]
        except Exception as e:
            logger.error(f"提取失败: {text[:50]}... - {str(e)}")
            raise


if __name__ == '__main__':
    import django

    django.setup()
    Command().execute()