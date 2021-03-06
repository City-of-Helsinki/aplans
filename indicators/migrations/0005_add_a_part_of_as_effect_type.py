# Generated by Django 2.1.3 on 2019-01-10 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indicators', '0004_add_related_indicators'),
    ]

    operations = [
        migrations.AlterField(
            model_name='relatedindicator',
            name='effect_type',
            field=models.CharField(choices=[('increases', 'increases'), ('decreases', 'decreases'), ('part_of', 'is a part of')], help_text='What type of causal effect is there between the indicators', max_length=40, verbose_name='effect type'),
        ),
    ]
