# recommender/admin.py
from django.contrib import admin
from .models import *
# Register your models here.


# CourseConcept中间模型的内联管理
class CourseConceptInline(admin.TabularInline):
    model = CourseConcept
    extra = 1
    autocomplete_fields = ['concept']  # 启用自动完成

# UserCourse中间模型的内联管理
class UserCourseInline(admin.TabularInline):
    model = UserCourse
    extra = 1

@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'parent')
    search_fields = ('name',)
    list_filter = ('parent__name',)
    raw_id_fields = ('parent',)  # 优化自关联字段显示

@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'field')
    search_fields = ('name', 'explanation')
    list_filter = ('field__name',)
    autocomplete_fields = ['field']  # 添加搜索框

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name', 'about')
    inlines = [CourseConceptInline]  # 使用内联替代filter_horizontal

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    inlines = [UserCourseInline]

@admin.register(CourseConcept)
class CourseConceptAdmin(admin.ModelAdmin):
    list_display = ('course', 'concept', 'weight')
    list_editable = ('weight',)
    raw_id_fields = ('course', 'concept')

@admin.register(UserCourse)
class UserCourseAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'enroll_time')
    list_filter = ('enroll_time',)
    date_hierarchy = 'enroll_time'

@admin.register(PrerequisiteDependency)
class PrerequisiteAdmin(admin.ModelAdmin):
    list_display = ('prerequisite', 'target')
    raw_id_fields = ('prerequisite', 'target')