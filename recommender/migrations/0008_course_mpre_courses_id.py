# Generated by Django 4.2.20 on 2025-05-06 18:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommender', '0007_remove_user_abstract_pre_courses_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='mpre_courses_id',
            field=models.JSONField(blank=True, db_column='mpre_courses_id', default=list, help_text='前继课程ID列表'),
        ),
    ]
