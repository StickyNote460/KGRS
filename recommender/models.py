from django.db import models


class Field(models.Model):
    """学科领域表（新增外键版本）"""
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'field'


class Concept(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    explanation = models.TextField()
    field = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'concept'


class Course(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    prerequisites = models.TextField()
    about = models.TextField()
    concepts = models.ManyToManyField(Concept, through='CourseConcept')

    class Meta:
        db_table = 'course'


class User(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)

    # 保持原始JSON结构的同时建立关系
    courses = models.ManyToManyField('Course', through='UserCourse')

    class Meta:
        db_table = 'user'


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

    class Meta:
        db_table = 'course_concept'
        unique_together = (('course', 'concept'),)


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