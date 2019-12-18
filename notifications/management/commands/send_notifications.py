import typing
from datetime import date, timedelta
from dataclasses import dataclass

from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import activate
from markupsafe import Markup

from actions.models import Plan, ActionTask, Action, ActionContactPerson
from people.models import Person
from notifications.models import NotificationType


MINIMUM_NOTIFICATION_PERIOD = 5  # days
TASK_DUE_SOON_DAYS = 30


@dataclass
class NotificationEmail:
    person: Person
    type: NotificationType
    context: dict

    def send(self):
        print(self.person.email)
        print(self.type)
        print(self.context)


class Notification:
    type: NotificationType
    plan: Plan
    obj: typing.Union[Action, ActionTask]

    def _get_type(self):
        return self.type.identifier

    def get_context(self):
        # Implement in subclass
        raise NotImplementedError()

    def mark_sent(self, person: Person):
        now = timezone.now()
        self.obj.sent_notifications.create(sent_at=now, person=person, type=self._get_type())

    def notification_last_sent(self, person: Person) -> typing.Optional[int]:
        last_notification = self.obj.sent_notifications.filter(
            person=person, type=self._get_type()
        ).order_by('-sent_at').first()
        if not last_notification:
            return None
        else:
            return (timezone.now() - last_notification.sent_at).days

    def _queue_notification(self, person: Person):
        person._notifications.setdefault(self._get_type(), []).append(self)


class TaskLateNotification(Notification):
    type = NotificationType.TASK_LATE

    def __init__(self, task: ActionTask, days_late: int):
        super().__init__()
        self.obj = task
        self.days_late = days_late

    def get_context(self):
        return dict(task=self.obj.get_notification_context(), days_late=self.days_late)

    def generate_notifications(self, action_contacts: typing.List[Person]):
        for person in action_contacts:
            days = self.notification_last_sent(person)
            if days is not None:
                if days < MINIMUM_NOTIFICATION_PERIOD:
                    # We don't want to remind too often
                    continue
                if self.days_late not in (1, 7) and not (self.days_late % 30 == 0):
                    # If we have reminded about this before, let's only
                    # send a reminder if it's late one day, a week or 30, 60, 90... days
                    continue
            else:
                # If we have never reminded about this, send a notification
                # no matter how many days are left.
                pass

            self._queue_notification(person)

        """
        msg = ngettext_lazy(
            "Task is %(days)d day late (due at %(date)s)",
            "Task is %(days)d days late (due at %(date)s)",
            'days'
        )
        task._to_send.append()
        return TaskNotification(task, notif_type, msg % {'days': -diff, 'date': due_at_str})
        """


class TaskDueSoonNotification(Notification):
    type = NotificationType.TASK_DUE_SOON

    def __init__(self, task: ActionTask, days_left: int):
        self.obj = task
        self.days_left = days_left

    def get_context(self):
        return dict(task=self.obj.get_notification_context(), days_left=self.days_left)

    def generate_notifications(self, action_contacts: typing.List[Person]):
        for person in action_contacts:
            days = self.notification_last_sent(person)
            if days is not None:
                if days < MINIMUM_NOTIFICATION_PERIOD:
                    # We don't want to remind too often
                    continue
                if self.days_left not in (1, 7, 30):
                    # If we have reminded about this before, let's only
                    # send a reminder if it's tomorrow, in a week or in a month
                    continue
            else:
                # If we have never reminded about this, send a notification
                # no matter how many days are left.
                pass

            self._queue_notification(person)

        """
        if False:
            msg = _("Task is due tomorrow")
        elif diff == 7:
            msg = _("Task is due in a week (due at %(date)s)") % {'date': due_at_str}
        elif diff == 30 or (diff < 30 and not self.was_notification_sent(action, notif_type)):
            # We also send a reminder if we've never reminded about this before.
            msg = ngettext_lazy(
                "Task deadline is %(days)d day away (due at %(date)s)",
                "Task deadline is %(days)d days away (due at %(date)s)",
                'days'
            ) % {'days': diff, 'date': due_at_str}
        else:
            return
        return TaskNotification(task, notif_type, msg)
        """


class NotEnoughTasksNotification(Notification):
    type = NotificationType.NOT_ENOUGH_TASKS

    def __init__(self, action: Action):
        self.obj = action

    def get_context(self):
        return dict(action=self.obj.get_notification_context())

    def generate_notifications(self):
        contacts = self.obj._contact_persons
        for person in contacts:
            days_since = self.notification_last_sent(person)
            if days_since is not None:
                if days_since < 30:
                    # We don't want to remind too often
                    continue

            self._queue_notification(person)


class ActionNotUpdatedNotification(Notification):
    pass


class NotificationEngine:
    def __init__(self, plan: Plan):
        self.plan = plan
        self.today = date.today()

        qs = ActionTask.objects.filter(action__plan=self.plan)
        qs = qs.exclude(state__in=(ActionTask.CANCELLED, ActionTask.COMPLETED))
        self.active_tasks = list(qs.order_by('due_at'))

        actions = self.plan.actions.all()
        for act in actions:
            act.plan = plan  # prevent DB query
            act._contact_persons = []  # same, filled in later
        self.actions_by_id = {act.id: act for act in actions}

        for task in self.active_tasks:
            task.action = self.actions_by_id[task.action_id]

        # notif_types = self.plan.notification_base_template.templates.values_list('type', flat=True)
        # notif_types = [x.identifier for x in NotificationType]

        action_contacts = ActionContactPerson.objects.filter(action__in=actions).select_related('person')
        persons_by_id = {}
        for ac in action_contacts:
            if ac.person_id not in persons_by_id:
                persons_by_id[ac.person_id] = ac.person
                ac.person._notifications = {}
            action = self.actions_by_id[ac.action_id]
            action._contact_persons.append(persons_by_id[ac.person_id])
        self.persons_by_id = persons_by_id

    def was_notification_sent(self, action: Action, type: str) -> bool:
        return action.sent_notifications.filter(type=type).exists()

    def generate_task_notifications(self, task: ActionTask):
        assert task.state not in (ActionTask.CANCELLED, ActionTask.COMPLETED)
        assert not task.completed_at

        diff = (task.due_at - self.today).days
        if diff < 0:
            # Task is late
            notif = TaskLateNotification(task, -diff)
        elif diff <= TASK_DUE_SOON_DAYS:
            # Task DL is coming
            notif = TaskDueSoonNotification(task, diff)
        else:
            return
        notif.generate_notifications(task.action._contact_persons)

    def make_action_notifications(self, action: Action):
        # Generate a notification if action doesn't have at least
        # three tasks with DLs within 365 days
        N_DAYS = 365
        TASK_COUNT = 1

        active_tasks = action.tasks.exclude(state__in=(ActionTask.CANCELLED, ActionTask.COMPLETED))
        today = date.today()
        count = 0
        for task in active_tasks:
            diff = (task.due_at - today).days
            if diff <= N_DAYS:
                count += 1
        if count < TASK_COUNT:
            notif = NotEnoughTasksNotification(action)
            notif.generate_notifications()

        if action.updated_at.date() - today >= timedelta(days=3 * 30):
            notif = ActionNotUpdatedNotification(action)
            notif.generate_notifications()

        return

    def generate_notifications(self):
        """
        for action in actions_by_id.values():
            action.tasks = []
            action._to_send = []
            self.make_action_notifications(action)
        """

        for task in self.active_tasks:
            self.generate_task_notifications(task)

        for action in self.actions_by_id.values():
            if action.status.is_completed:
                continue
            self.make_action_notifications(action)

        base_template = self.plan.notification_base_template
        templates_by_type = {t.type: t for t in base_template.templates.all()}
        for person in self.persons_by_id.values():
            for ttype, notifications in person._notifications.items():
                if ttype != 'not_enough_tasks':
                    continue
                template = templates_by_type.get(ttype)
                if template is None:
                    print('No template for %s' % ttype)
                    continue

                cb_qs = base_template.content_blocks.filter(Q(template__isnull=True) | Q(template=template))
                content_blocks = {cb.identifier: Markup(cb.content) for cb in cb_qs}

                context = {
                    'items': [x.get_context() for x in notifications],
                    'person': person.get_notification_context(),
                    'content_blocks': content_blocks,
                }
                rendered = template.render(context)
                msg = EmailMessage(
                    rendered['subject'],
                    rendered['html_body'],
                    'Helsingin ilmastovahti <noreply@ilmastovahti.fi>',
                    # ['sonja-maria.ignatius@hel.fi']
                    ['juha.yrjola@gmail.com']
                )
                msg.content_subtype = "html"  # Main content is now text/html
                print('sending %s to %s' % (rendered['subject'], person))
                for n in notifications:
                    print('\t%s' % n.obj)

                # msg.send()
                for n in notifications:
                    n.mark_sent(person)

        exit()

        """
        actions = sorted(actions_by_id.values(), key=lambda x: x.order)
        for action in actions:
            if not action._to_send:
                continue
            print(action)
            continue
            for notif in action._to_send:
                if isinstance(notif, ActionNotification):
                    print('\t%s' % notif.message)
                else:
                    print('\t%s: %s' % (notif.task, notif.message))
        """

"""
Toimenpide 145. Toimenpideohjelman arvioinnin työkalut
Tehtävä On sovittu, miten KILTOVA-työtä jatketaan, deadline 12 päivän päästä (15.12.2019)
Tehtävä Määritellään mittareille standardirajapinnat, deadline 28 päivän päästä (31.12.2019)
"""


class ActionNotification:
    def __init__(self, action, type, message):
        self.action = action
        self.message = message
        self.type = type


class Command(BaseCommand):
    help = 'Recalculates statuses and completions for all actions'

    def add_arguments(self, parser):
        parser.add_argument('--plan', type=str, help='Identifier of the action plan')

    def handle(self, *args, **options):
        if not options['plan']:
            raise CommandError('No plan supplied')

        activate(settings.LANGUAGES[0][0])

        plan = Plan.objects.get(identifier=options['plan'])
        engine = NotificationEngine(plan)
        engine.generate_notifications()
