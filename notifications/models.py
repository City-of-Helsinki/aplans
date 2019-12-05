import logging
from enum import Enum
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from jinja2 import StrictUndefined
from jinja2.exceptions import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from parler.models import TranslatableModel, TranslatedFields
from parler.utils.context import switch_language

from actions.models import Plan
from people.models import Person


DEFAULT_LANG = settings.LANGUAGES[0][0]
logger = logging.getLogger('aplans.notifications')


class NotificationType(Enum):
    TASK_LATE = _("Task is late")
    TASK_DUE_SOON = _("Task is due soon")
    ACTION_NOT_UPDATED = _("Action metadata has not been updated recently")
    NOT_ENOUGH_TASKS = _("Action doesn't have enough in-progress tasks")

    @property
    def identifier(self):
        return self.name.lower()

    @property
    def verbose_name(self):
        return self.value


def notification_type_choice_builder():
    for val in NotificationType:
        yield (val.identifier, val.verbose_name)


class NotificationTemplateException(Exception):
    pass


class SentNotification(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    sent_at = models.DateTimeField()
    type = models.CharField(
        verbose_name=_('type'), choices=notification_type_choice_builder(),
        max_length=100
    )
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='notifications')

    def __str__(self):
        return '%s: %s' % (self.action, self.type)


class BaseTemplate(models.Model):
    plan = models.OneToOneField(
        Plan, on_delete=models.CASCADE, related_name='notification_base_template',
        verbose_name=_('plan'),
    )
    html_body = models.TextField(verbose_name=_('HTML body'))

    class Meta:
        verbose_name = _('base template')
        verbose_name_plural = _('base templates')

    def __str__(self):
        return str(self.plan)

    def render(self, content):
        env = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)
        context = dict(content=content)
        try:
            html = env.from_string(self.html_body).render(context)
        except TemplateError as e:
            raise NotificationTemplateException(e) from e
        return html


class NotificationTemplate(TranslatableModel):
    base = models.ForeignKey(BaseTemplate, on_delete=models.CASCADE, related_name='templates', editable=False)
    type = models.CharField(
        verbose_name=_('type'), choices=notification_type_choice_builder(),
        max_length=100, unique=True, db_index=True
    )

    translations = TranslatedFields(
        subject=models.CharField(
            verbose_name=_('subject'), max_length=200, help_text=_('Subject for email notifications')
        ),
        html_body=models.TextField(
            verbose_name=_('HTML body'), help_text=_('HTML body for email notifications'),
        )
    )

    class Meta:
        verbose_name = _('notification template')
        verbose_name_plural = _('notification templates')
        unique_together = (('base', 'type'),)

    def __str__(self):
        for val in NotificationType:
            if val.identifier == self.type:
                return str(val.verbose_name)
        return 'N/A'

    def render(self, context, language_code=DEFAULT_LANG):
        env = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)

        logger.debug('Rendering template for notification %s' % self.type)
        with switch_language(self, language_code):
            try:
                rendered_notification = {
                    attr: env.from_string(getattr(self, attr)).render(context)
                    for attr in ('subject', 'html_body')
                }
            except TemplateError as e:
                raise NotificationTemplateException(e) from e

        rendered_notification['html_body'] = self.base.render(rendered_notification['html_body'])
        return rendered_notification

    def clean(self):
        pass
