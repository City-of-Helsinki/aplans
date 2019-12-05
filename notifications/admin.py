from ckeditor.widgets import CKEditorWidget
from django.contrib import admin
from parler.admin import TranslatableAdmin
from parler.forms import TranslatableModelForm

from admin_site.admin import AplansModelAdmin
from .models import BaseTemplate, NotificationTemplate, ContentBlock


@admin.register(BaseTemplate)
class BaseTemplateAdmin(AplansModelAdmin):
    fields = [
        'html_body'
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        plan = request.user.get_active_admin_plan()
        return qs.filter(plan=plan)

    def save_model(self, request, obj, form, change):
        obj.plan = request.user.get_active_admin_plan()
        super().save_model(request, obj, form, change)


class NotificationTemplateForm(TranslatableModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Do not allow the admin to choose any of the template types that already
        # exist.
        qs = NotificationTemplate.objects.values_list('type', flat=True)
        if self.instance and self.instance.type:
            qs = qs.exclude(id=self.instance.id)
        existing_types = set(qs)
        choices = [x for x in self.fields['type'].choices if x[0] not in existing_types]
        self.fields['type'].choices = choices


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(AplansModelAdmin, TranslatableAdmin):
    form = NotificationTemplateForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        plan = request.user.get_active_admin_plan()
        return qs.filter(base__plan=plan)

    def save_model(self, request, obj, form, change):
        plan = request.user.get_active_admin_plan()
        obj.base = plan.notification_base_template
        super().save_model(request, obj, form, change)


@admin.register(ContentBlock)
class ContentBlockAdmin(AplansModelAdmin, TranslatableAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        plan = request.user.get_active_admin_plan()
        return qs.filter(base__plan=plan)

    def save_model(self, request, obj, form, change):
        plan = request.user.get_active_admin_plan()
        obj.base = plan.notification_base_template
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'content' in form.base_fields:
            form.base_fields['content'].widget = CKEditorWidget(config_name='lite')
        return form
