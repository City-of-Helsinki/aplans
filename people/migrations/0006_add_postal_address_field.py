# Generated by Django 2.2.8 on 2019-12-10 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0005_add_person_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='postal_address',
            field=models.TextField(blank=True, max_length=100, null=True, verbose_name='postal address'),
        ),
    ]
