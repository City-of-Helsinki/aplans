from datetime import date

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from django_orghierarchy.models import Organization
from ordered_model.models import OrderedModel
from aplans.utils import IdentifierField
from aplans.model_images import ModelWithImage

from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel
from wagtail.core.models import Orderable

from wagtailautocomplete.edit_handlers import AutocompletePanel

from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalKey, ParentalManyToManyField


User = get_user_model()


class Plan(ModelWithImage, models.Model):
    name = models.CharField(max_length=100, verbose_name=_('name'))
    identifier = IdentifierField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    actions_locked = models.BooleanField(
        default=False, verbose_name=_('actions locked'),
        help_text=_('Can actions be added and the official metadata edited?'),
    )

    general_admins = models.ManyToManyField(
        User, blank=True, related_name='general_admin_plans',
        verbose_name=_('general administrators'),
        help_text=_('Users that can modify everything related to the action plan')
    )

    class Meta:
        verbose_name = _('plan')
        verbose_name_plural = _('plans')
        get_latest_by = 'created_at'
        ordering = ('created_at',)

    def __str__(self):
        return self.name

    def get_last_action_identifier(self):
        return self.actions.order_by('order').values_list('identifier', flat=True).last()


def latest_plan():
    if Plan.objects.exists():
        return Plan.objects.latest().id
    else:
        return None


class Action(ModelWithImage, OrderedModel, ClusterableModel):
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, default=latest_plan, related_name='actions',
        verbose_name=_('plan')
    )
    name = models.CharField(max_length=1000, verbose_name=_('name'))
    official_name = models.TextField(
        null=True, blank=True,
        verbose_name=_('official name'),
        help_text=_('The name as approved by an official party')
    )
    identifier = IdentifierField(
        help_text=_('The identifier for this action (e.g. number)')
    )
    description = RichTextField(
        verbose_name=_('description'),
        help_text=_('What does this action involve in more detail?'),
        default='',
    )
    impact = models.IntegerField(
        null=True, blank=True,
        verbose_name=_('impact'),
        help_text=_('The impact this action has in measurable quantity (e.g. t CO₂e)')
    )
    status = models.ForeignKey(
        'ActionStatus', blank=True, null=True, on_delete=models.SET_NULL,
        verbose_name=_('status'),
    )
    completion = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_('completion'), editable=False,
        help_text=_('The completion percentage for this action')
    )
    schedule = models.ManyToManyField(
        'ActionSchedule', blank=True,
        verbose_name=_('schedule')
    )
    decision_level = models.ForeignKey(
        'ActionDecisionLevel', blank=True, null=True, related_name='actions', on_delete=models.SET_NULL,
        verbose_name=_('decision-making level')
    )
    responsible_parties = ParentalManyToManyField(
        Organization, through='ActionResponsibleParty', blank=True,
        related_name='responsible_actions', verbose_name=_('responsible parties')
    )
    categories = models.ManyToManyField(
        'Category', blank=True, verbose_name=_('categories')
    )
    indicators = models.ManyToManyField(
        'indicators.Indicator', blank=True, verbose_name=_('indicators'),
        through='indicators.ActionIndicator', related_name='actions'
    )

    contact_persons = models.ManyToManyField(
        'people.Person', blank=True, verbose_name=_('contact persons'),
        related_name='contact_for_actions'
    )

    updated_at = models.DateTimeField(
        auto_now=True, editable=False, verbose_name=_('updated at')
    )

    order_with_respect_to = 'plan'

    class Meta:
        verbose_name = _('action')
        verbose_name_plural = _('actions')
        ordering = ('plan', 'order')
        index_together = (('plan', 'order'),)
        permissions = (
            ('admin_action', _("Can administrate all actions")),
        )

    def __str__(self):
        return "%s. %s" % (self.identifier, self.name)

    def clean(self):
        # FIXME: Make sure FKs and M2Ms point to objects that are within the
        # same action plan.
        super().clean()

    def get_next_action(self):
        return Action.objects.filter(plan=self.plan_id, order__gt=self.order).first()

    def get_previous_action(self):
        return Action.objects.filter(plan=self.plan_id, order__lt=self.order).order_by('-order').first()

    def _calculate_completion(self, tasks):
        n_completed = len(list(filter(lambda x: x.completed_at is not None, tasks)))
        return n_completed * 100 / len(tasks)

    def _determine_status(self, tasks):
        statuses = self.plan.action_statuses.all()
        by_id = {x.identifier: x for x in statuses}
        KNOWN_IDS = {'not_started', 'on_time', 'late', 'severely_late'}
        # If the status set is not something we can handle, bail out.
        if not KNOWN_IDS.issubset(set(by_id.keys())):
            return None

        today = date.today()

        def is_late(task):
            if task.due_at is None or task.completed_at is not None:
                return False
            return today > task.due_at

        late_tasks = list(filter(is_late, tasks))
        if not late_tasks:
            completed_tasks = list(filter(lambda x: x.completed_at is not None, tasks))
            if not completed_tasks:
                return by_id['not_started']
            else:
                return by_id['on_time']

        if len(late_tasks) == len(tasks) and len(late_tasks) > 1:
            return by_id['severely_late']
        else:
            return by_id['late']

    def recalculate_status(self):
        tasks = self.tasks.exclude(state=ActionTask.CANCELLED).only('due_at', 'completed_at')
        if not tasks:
            return

        self.completion = self._calculate_completion(tasks)
        update_fields = ['completion']
        status = self._determine_status(tasks)
        if status is not None:
            self.status = status
            update_fields.append('status')
        self.save(update_fields=update_fields)

    def task_updated(self, task):
        self.recalculate_status()

    def has_contact_persons(self):
        return self.contact_persons.exists()
    has_contact_persons.short_description = _('Has contact persons')
    has_contact_persons.boolean = True

    def active_task_count(self):
        return self.tasks.exclude(state=ActionTask.CANCELLED).filter(completed_at__isnull=True).count()
    active_task_count.short_description = _('Active tasks')

    panels = [
        FieldPanel('name'),
        FieldPanel('description'),
        AutocompletePanel('responsible_parties', target_model='django_orghierarchy.Organization', is_single=False),
    ]


class ActionResponsibleParty(OrderedModel, Orderable):
    action = models.ForeignKey(
        'actions.Action',
        on_delete=models.CASCADE,
        verbose_name=_('action'),
        related_name='+'
    )
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, verbose_name=_('organization'),
        limit_choices_to=Q(dissolution_date=None)
    )

    order_with_respect_to = 'action'

    class Meta:
        ordering = ['action', 'order']
        index_together = (('action', 'order'),)
        verbose_name = _('action responsible party')
        verbose_name_plural = _('action responsible parties')


class ActionSchedule(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='action_schedules')
    name = models.CharField(max_length=100)
    begins_at = models.DateField()
    ends_at = models.DateField(null=True, blank=True)

    class Meta(OrderedModel.Meta):
        ordering = ('plan', 'begins_at')
        verbose_name = _('action schedule')
        verbose_name_plural = _('action schedules')

    def __str__(self):
        return self.name


class ActionStatus(models.Model):
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name='action_statuses',
        verbose_name=_('plan')
    )
    name = models.CharField(max_length=50, verbose_name=_('name'))
    identifier = IdentifierField(max_length=20)

    class Meta:
        unique_together = (('plan', 'identifier'),)
        verbose_name = _('action status')
        verbose_name_plural = _('action statuses')

    def __str__(self):
        return self.name


class ActionDecisionLevel(models.Model):
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name='action_decision_levels',
        verbose_name=_('plan')
    )
    name = models.CharField(max_length=200, verbose_name=_('name'))
    identifier = IdentifierField()

    class Meta:
        unique_together = (('plan', 'identifier'),)

    def __str__(self):
        return self.name


class ActionTask(models.Model):
    ACTIVE = 'active'
    CANCELLED = 'cancelled'
    STATES = (
        (ACTIVE, _('active')),
        (CANCELLED, _('cancelled')),
    )

    action = models.ForeignKey(
        Action, on_delete=models.CASCADE, related_name='tasks',
        verbose_name=_('action')
    )
    name = models.CharField(max_length=200, verbose_name=_('name'))
    state = models.CharField(max_length=20, choices=STATES, default=ACTIVE, verbose_name=_('state'))
    comment = models.TextField(null=True, blank=True, verbose_name=_('comment'))
    due_at = models.DateField(null=True, blank=True, verbose_name=_('due date'))
    completed_at = models.DateField(null=True, blank=True, verbose_name=_('completion date'))

    completed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_('completed by'), editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name=_('created at'))
    modified_at = models.DateTimeField(auto_now=True, editable=False, verbose_name=_('modified at'))

    class Meta:
        ordering = ('action', 'due_at')
        verbose_name = _('action task')
        verbose_name_plural = _('action tasks')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.action.task_updated(self)


class CategoryType(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='category_types')
    name = models.CharField(max_length=50)
    identifier = IdentifierField()

    class Meta:
        unique_together = (('plan', 'identifier'),)
        ordering = ('plan', 'name')
        verbose_name = _('category type')
        verbose_name_plural = _('category types')

    def __str__(self):
        return "%s (%s:%s)" % (self.name, self.plan.identifier, self.identifier)


class Category(OrderedModel, ModelWithImage):
    type = models.ForeignKey(
        CategoryType, on_delete=models.CASCADE, related_name='categories',
        verbose_name=_('type')
    )
    identifier = IdentifierField()
    name = models.CharField(max_length=100, verbose_name=_('name'))
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children',
        verbose_name=_('parent category')
    )

    order_with_respect_to = 'type'

    class Meta:
        unique_together = (('type', 'identifier'),)
        verbose_name = _('category')
        verbose_name_plural = _('categories')
        ordering = ('type', 'identifier')

    def __str__(self):
        return "%s %s" % (self.identifier, self.name)


class Scenario(models.Model):
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name='scenarios',
        verbose_name=_('plan')
    )
    name = models.CharField(max_length=100, verbose_name=_('name'))
    identifier = IdentifierField()
    description = models.TextField(null=True, blank=True, verbose_name=_('description'))

    class Meta:
        unique_together = (('plan', 'identifier'),)
        verbose_name = _('scenario')
        verbose_name_plural = _('scenarios')

    def __str__(self):
        return self.name
