from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import (
    Action, ActionResponsibleParty, ActionTask, Plan, ActionSchedule,
    ActionStatus, Category, CategoryType, ActionImpact, ActionContactPerson,
    ActionStatusUpdate,
)
from django_orghierarchy.models import Organization
from indicators.models import (
    ActionIndicator, Indicator, RelatedIndicator, Unit, IndicatorLevel,
    IndicatorGraph, IndicatorGoal, IndicatorValue, Quantity,
    IndicatorContactPerson, Dataset, DatasetLicense
)
from content.models import (
    StaticPage, BlogPost, Question, SiteGeneralContent
)
from notifications.models import (
    BaseTemplate, NotificationTemplate, ContentBlock
)
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from people.models import Person


User = get_user_model()


ACTIONS_APP = 'actions'

ALL_PERMS = ('view', 'change', 'delete', 'add')


def _get_perm_objs(model, perms):
    content_type = ContentType.objects.get_for_model(model)
    perms = ['%s_%s' % (x, model._meta.model_name) for x in perms]
    perm_objs = Permission.objects.filter(content_type=content_type, codename__in=perms)
    return list(perm_objs)


def get_contact_person_perms():
    new_perms = []

    # Add general permissions
    new_perms += _get_perm_objs(Action, ('view', 'change'))
    new_perms += _get_perm_objs(ActionTask, ('view', 'change', 'delete', 'add'))
    new_perms += _get_perm_objs(Person, ('view', 'change', 'add'))
    new_perms += _get_perm_objs(ActionContactPerson, ALL_PERMS)
    new_perms += _get_perm_objs(ActionStatusUpdate, ALL_PERMS)
    new_perms += _get_perm_objs(ActionIndicator, ('view',))
    new_perms += _get_perm_objs(Indicator, ('view',))

    for model in (
        ActionResponsibleParty,
    ):
        new_perms += _get_perm_objs(model, ALL_PERMS)
    new_perms += _get_perm_objs(Organization, ('view',))

    return new_perms


def _get_or_create_group(name, perms=None):
    group, _ = Group.objects.get_or_create(name=name)

    if perms is None:
        return group

    existing_perms = set(list(group.permissions.all()))
    new_perms = set(perms)
    if existing_perms != new_perms:
        group.permissions.clear()
        group.permissions.add(*new_perms)

    return group


def get_or_create_contact_person_group():
    perms = get_contact_person_perms()
    group = _get_or_create_group('Action contact persons', perms)
    return group


def add_contact_person_perms(user):
    group = get_or_create_contact_person_group()
    user.groups.add(group)

    # Make sure user is able to access the admin UI
    if not user.is_staff:
        user.is_staff = True
        user.save(update_fields=['is_staff'])


def remove_contact_person_perms(user):
    group = get_or_create_contact_person_group()
    user.groups.remove(group)


PLAN_ADMIN_PERMS = (
    (Plan, ('view', 'change')),
    (Action, ALL_PERMS),
    (ActionStatus, ALL_PERMS),
    (ActionSchedule, ALL_PERMS),
    (ActionImpact, ALL_PERMS),
    (CategoryType, ALL_PERMS),
    (Category, ALL_PERMS),

    (IndicatorLevel, ALL_PERMS),
    (ActionIndicator, ALL_PERMS),
    (Indicator, ALL_PERMS),
    (IndicatorGraph, ALL_PERMS),
    (IndicatorGoal, ALL_PERMS),
    (IndicatorValue, ALL_PERMS),
    (IndicatorContactPerson, ALL_PERMS),
    (RelatedIndicator, ALL_PERMS),
    (Unit, ALL_PERMS),
    (Quantity, ALL_PERMS),
    (Dataset, ALL_PERMS),
    (DatasetLicense, ALL_PERMS),

    (Person, ALL_PERMS),  # also delete perm for plan admin

    (StaticPage, ALL_PERMS),
    (BlogPost, ALL_PERMS),
    (Question, ALL_PERMS),
    (SiteGeneralContent, ('add', 'view', 'change')),

    (BaseTemplate, ('add', 'view', 'change')),
    (NotificationTemplate, ALL_PERMS),
    (ContentBlock, ALL_PERMS),

    (User, ('view',))
)


def get_plan_admin_perms():
    all_perms = get_contact_person_perms()
    for model, perms in PLAN_ADMIN_PERMS:
        all_perms += _get_perm_objs(model, perms)

    return all_perms


def get_or_create_plan_admin_group():
    perms = get_plan_admin_perms()
    group = _get_or_create_group('Plan admins', perms)
    return group


def remove_plan_admin_perms(user):
    group = get_or_create_plan_admin_group()
    user.groups.remove(group)


def add_plan_admin_perms(user):
    group = get_or_create_plan_admin_group()
    user.groups.add(group)

    if not user.is_staff:
        user.is_staff = True
        user.save(update_fields=['is_staff'])


class ActionRelatedAdminPermMixin:
    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if not isinstance(obj, Action):
            obj = None
        return request.user.can_modify_action(obj)

    def has_add_permission(self, request, obj=None):
        if not super().has_add_permission(request, obj):
            return False
        if not isinstance(obj, Action):
            obj = None
        return request.user.can_modify_action(obj)

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if not isinstance(obj, Action):
            obj = None
        return request.user.can_modify_action(obj)
