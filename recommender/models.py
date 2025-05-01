from django.db import models
from django.db.models import Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import math
'''
save()：保存对象到数据库。
delete()：从数据库中删除对象。
objects：默认的模型管理器（Manager），用于数据库查询（如 all()、filter()、get() 等）。
'''

#定义一个名为 Field 的 Django 模型类，继承自 models.Model。
# Django 会自动将该类映射到数据库中的一张表。
class Field(models.Model):
    """学科领域表（新增外键版本）"""
    #CharField 是 django.db.models 模块中的一个类，用于定义字符类型的字段。
    #显式指定的参数，表示将该字段设置为主键（Primary Key）
    #否則，Django 会自动创建一个名为 id 的自增主键字段。
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    #Meta 类用于配置模型的元数据（metadata），例如表名、多语言名称、索引等。
    class Meta:
        db_table = 'field' #指定数据库中的表名为 field（默认表名是 app名_field）
        #25.4.30 20:39新增
        verbose_name = '学科领域'
        verbose_name_plural = '学科领域'
        indexes = [models.Index(fields=['name'])]

class Concept(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    explanation = models.TextField()
    field = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True)
    # 新增字段开始 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    depth = models.IntegerField(
        default=0,
        verbose_name='层级深度',
        help_text='从根领域到当前概念的最长路径深度（自动计算）'
    )
    dependency_count = models.IntegerField(
        default=0,
        verbose_name='被依赖次数',
        help_text='被其他概念作为直接先修条件的次数（实时统计）'
    )
    # 新增字段结束 <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    class Meta:
        db_table = 'concept'
        #新增
        verbose_name = '知识概念'
        verbose_name_plural = '知识概念'
        indexes = [
            models.Index(fields=['depth'], name='concept_depth_idx'),
            models.Index(fields=['dependency_count'], name='concept_dependency_idx')
        ]

class Course(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    prerequisites = models.TextField()
    about = models.TextField()
    concepts = models.ManyToManyField(Concept, through='CourseConcept')
    # 新增字段开始 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    video_name = models.JSONField(
        default=list,
        verbose_name='教学视频序列',
        help_text='课程包含的教学视频名称有序列表，格式示例：["视频1", "视频2", ...]'
    )
    popularity = models.IntegerField(
        default=0,
        verbose_name='课程热度',
        help_text='基于用户学习次数计算的课程热度（每日更新）'
    )
    difficulty = models.FloatField(
        default=1.0,
        verbose_name='课程难度',
        help_text='基于关联概念平均深度计算的难度系数（周更新）'
    )

    # 新增字段结束 <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    class Meta:
        db_table = 'course'
        #新增
        verbose_name = '课程信息'
        verbose_name_plural = '课程信息'

class User(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)

    # 保持原始JSON结构的同时建立关系
    courses = models.ManyToManyField('Course', through='UserCourse')

    # 新增字段开始 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    learning_style = models.JSONField(
        null=True,
        blank=True,
        verbose_name='学习风格向量',
        help_text='用户历史学习领域分布的概率向量（格式：{"领域名": 概率值}）'
    )

    # 新增字段结束 <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    class Meta:
        db_table = 'user'
        verbose_name = '用户信息'
        verbose_name_plural = '用户信息'


# 在User模型中添加方法
def calculate_learning_style(self):
    """优化后的学习风格计算方法（使用prefetch_related）"""
    from collections import defaultdict

    # 通过prefetch_related一次性获取所有关联数据
    user_courses = self.usercourse_set.select_related('course').prefetch_related(
        'course__concepts__field'
    )

    field_counter = defaultdict(int)
    total = 0

    # 遍历预取的数据（无额外查询）
    for user_course in user_courses:
        # 获取课程关联的所有概念及其领域
        concepts = user_course.course.concepts.all()
        for concept in concepts:
            if concept.field:
                field_name = concept.field.name
                field_counter[field_name] += 1
                total += 1

    # 计算概率分布（保持原始逻辑）
    return {
        field: (count / total) if total > 0 else 0.0
        for field, count in field_counter.items()
    }



# 以下是需要补充的关系表模型
class ConceptFieldRelation(models.Model):
    """概念-领域关系表（带外键版本）"""
    concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        db_column='concept_id'  # 显式指定数据库列名
    )
    field = models.ForeignKey(
        Field,
        on_delete=models.CASCADE,
        db_column='field_id'
    )

    class Meta:
        db_table = 'concept_field_relation'
        unique_together = (('concept', 'field'),)


class ParentSonRelation(models.Model):
    """父子关系表（带外键版本）"""
    parent = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name='children',
        db_column='parent_id'
    )
    son = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name='parents',
        db_column='son_id'
    )

    class Meta:
        db_table = 'parent_son_relation'
        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['son'])
        ]


class CourseConcept(models.Model):
    """课程-知识点关系表（优化版）"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE)
    weight = models.FloatField(default=1.0)  # 为推荐系统预留权重字段

    # 新增字段开始 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    normalized_weight = models.FloatField(
        default=0.0,
        verbose_name='归一化权重',
        help_text='综合领域深度和被依赖次数的归一化权重（0.0~1.0）'
    )

    # 新增字段结束 <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    class Meta:
        db_table = 'course_concept'
        unique_together = (('course', 'concept'),)
        verbose_name = '课程-概念关系'
        verbose_name_plural = '课程-概念关系'
    #新增方法
    @property
    def intelligent_weight(self):
        """智能权重计算（不存储，动态计算）"""
        # 基础指标
        base = 0.3 * self.concept.dependency_count + 0.2 * (1 / (self.concept.depth + 1))

        # 课程相关性（TF-IDF）
        total_concepts = self.course.concepts.count()
        concept_freq = Concept.objects.filter(
            courseconcept__course=self.course,
            id=self.concept.id
        ).count()
        tf = concept_freq / total_concepts

        idf = math.log(Course.objects.count() / (1 + Concept.objects.filter(
            courseconcept__concept=self.concept
        ).count()))

        # 用户行为因子
        completion_rate = UserCourse.objects.filter(
            course=self.course,
            user__usercourse__isnull=False
        ).count() / max(1, UserCourse.objects.filter(course=self.course).count())

        return base * (tf * idf) * (1 + completion_rate)

class UserCourse(models.Model):
    """用户-课程关系表（带时间戳）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enroll_time = models.DateTimeField()  # 拆解原始JSON数组
    order = models.PositiveIntegerField()  # 学习顺序

    class Meta:
        db_table = 'user_course'
        ordering = ['order']
        unique_together = (('user', 'course'),)
#
# # 信号处理（用户选课时更新）
# @receiver(post_save, sender=UserCourse)
# def update_learning_style(sender, instance, **kwargs):
#     instance.user.learning_style = instance.user.calculate_learning_style()
#     instance.user.save()

class PrerequisiteDependency(models.Model):
    """先修依赖关系表（优化版）"""
    prerequisite = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name='required_by'
    )
    target = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name='dependencies'
    )

    class Meta:
        db_table = 'prerequisite_dependency'
        unique_together = (('prerequisite', 'target'),)