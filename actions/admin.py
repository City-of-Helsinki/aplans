from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ordered_model.admin import OrderedTabularInline, OrderedInlineModelAdminMixin, \
    OrderedModelAdmin
from django_summernote.admin import SummernoteModelAdmin
from django_summernote.widgets import SummernoteWidget
from image_cropping import ImageCroppingMixin

from django_orghierarchy.admin import OrganizationAdmin as DefaultOrganizationAdmin
from django_orghierarchy.models import Organization

from indicators.admin import ActionIndicatorAdmin
from .models import Plan, Action, ActionSchedule, ActionResponsibleParty, Scenario, \
    Category, CategoryType, ActionTask, ActionStatus
from .perms import ActionRelatedAdminPermMixin


class ActionScheduleAdmin(OrderedTabularInline):
    model = ActionSchedule
    extra = 0
    fields = ('name', 'begins_at', 'ends_at', 'move_up_down_links',)
    readonly_fields = ('move_up_down_links',)
    ordering = ('order',)


class ScenarioAdmin(admin.StackedInline):
    model = Scenario
    extra = 0


class ActionStatusAdmin(admin.TabularInline):
    model = ActionStatus
    extra = 0


class CategoryTypeAdmin(admin.StackedInline):
    model = CategoryType
    extra = 0


@admin.register(Plan)
class PlanAdmin(ImageCroppingMixin, OrderedInlineModelAdminMixin, admin.ModelAdmin):
    autocomplete_fields = ('general_admins',)
    inlines = [
        ActionStatusAdmin, ActionScheduleAdmin, ScenarioAdmin, CategoryTypeAdmin
    ]


class ActionResponsiblePartyAdmin(ActionRelatedAdminPermMixin, OrderedTabularInline):
    model = ActionResponsibleParty
    extra = 0
    # fields = ('org', 'move_up_down_links',)
    # readonly_fields = ('move_up_down_links',)
    fields = ('org',)
    ordering = ('order',)
    autocomplete_fields = ('org',)


class ActionTaskAdmin(ActionRelatedAdminPermMixin, admin.StackedInline):
    model = ActionTask
    summernote_fields = ('comment',)
    extra = 0

    def get_formset(self, *args, **kwargs):
        formset = super().get_formset(*args, **kwargs)
        formset.form.base_fields['comment'].widget = SummernoteWidget()
        return formset


@admin.register(Action)
class ActionAdmin(ImageCroppingMixin, OrderedModelAdmin, SummernoteModelAdmin):
    summernote_fields = ('description', 'official_name')
    search_fields = ('name', 'identifier')
    readonly_fields = (
        'official_name', 'identifier', 'status', 'completion',
        'categories',)
    autocomplete_fields = ('contact_persons',)

    fieldsets = (
        (_('Basic information'), {
            'fields': (
                'plan', 'identifier', 'official_name', 'name', 'description',
                'categories', 'contact_persons', 'image', 'image_cropping',
                'schedule', 'decision_level',
            ),
            'classes': ('baton-tabs-init', 'baton-tab-inline-tasks',)
        }),
        (None, {
            'fields': ('status', 'completion')
        }),
    )

    inlines = [
        ActionResponsiblePartyAdmin, ActionIndicatorAdmin, ActionTaskAdmin
    ]

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False

        # The user has view permission to all actions if he is either
        # a general admin for actions or a contact person for any
        # actions.
        user = request.user
        if user.is_superuser or user.has_perm('actions.admin_action'):
            return True

        return user.is_contact_person_for_action(None)

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False

        user = request.user
        return user.can_modify_action(obj)


@admin.register(Category)
class CategoryAdmin(ImageCroppingMixin, OrderedModelAdmin):
    pass


admin.site.unregister(Organization)


@admin.register(Organization)
class OrganizationAdmin(DefaultOrganizationAdmin):
    search_fields = ('name', 'abbreviation')

    def get_queryset(self, request):
        # The default OrganizationAdmin is buggy
        qs = admin.ModelAdmin.get_queryset(self, request).filter(dissolution_date=None)
        return qs

    def get_actions(self, request):
        return admin.ModelAdmin.get_actions(self, request)
