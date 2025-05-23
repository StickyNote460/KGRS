# Generated by Django 4.2.20 on 2025-05-06 02:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommender', '0006_user_abstract_pre_courses_user_match_pre_courses'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='abstract_pre_courses',
        ),
        migrations.RemoveField(
            model_name='user',
            name='match_pre_courses',
        ),
        migrations.AddField(
            model_name='course',
            name='abstract_pre_courses',
            field=models.JSONField(blank=True, default=list, help_text='从课程先修字段中提取的候选先修课程列表'),
        ),
        migrations.AddField(
            model_name='course',
            name='match_pre_courses',
            field=models.JSONField(blank=True, default=list, help_text='根据候选课程匹配得到的最合适的先修课程列表'),
        ),
        migrations.AddIndex(
            model_name='courseconcept',
            index=models.Index(fields=['course'], name='idx_courseconcept_course'),
        ),
        migrations.AddIndex(
            model_name='usercourse',
            index=models.Index(fields=['user'], name='idx_usercourse_user'),
        ),
    ]
