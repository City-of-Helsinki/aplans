# Generated by Django 2.2.6 on 2019-11-29 11:51

from django.db import migrations


def migrate_actiontask_state(apps, schema_editor):
    ActionTask = apps.get_model('actions', 'ActionTask')
    for at in ActionTask.objects.all():
        if at.state == 'cancelled':
            continue

        if at.completed_at is not None:
            new_state = 'completed'
        else:
            new_state = 'in_progress'
        at.state = new_state
        at.save(update_fields=['state'])


class Migration(migrations.Migration):
    dependencies = [
        ('actions', '0034_change_actiontask_states'),
    ]

    operations = [
        migrations.RunPython(migrate_actiontask_state),
    ]