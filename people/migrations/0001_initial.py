# Generated by Django 2.1.3 on 2018-12-14 18:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('django_orghierarchy', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100, verbose_name='first name')),
                ('last_name', models.CharField(max_length=100, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='email address')),
                ('organization', models.ForeignKey(blank=True, help_text='Set if this person is part of an organization', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='people', to='django_orghierarchy.Organization', verbose_name='organization')),
                ('user', models.OneToOneField(blank=True, help_text='Set if the person has an user account', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='person', to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
        ),
    ]
