import logging
from enum import Enum
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import translation
from django.utils.formats import date_format
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


class NotificationTemplateException(Exception):
    pass


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


def format_date(dt):
    current_language = translation.get_language()
    if current_language == 'fi':
        dt_format = r'j.n.Y'
    else:
        # default to English
        dt_format = r'j/n/Y'

    return date_format(dt, dt_format)


def make_jinja_environment():
    env = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)
    env.filters['format_date'] = format_date
    return env


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
        return '%s: %s -> %s' % (self.content_object, self.type, self.person)


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
        context = dict(content=content)
        env = make_jinja_environment()
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
        env = make_jinja_environment()
        logger.debug('Rendering template for notification %s' % self.type)
        with switch_language(self, language_code):
            rendered_notification = {}
            for attr in ('subject', 'html_body'):
                try:
                    rendered_notification[attr] = \
                        env.from_string(getattr(self, attr)).render(context)
                except TemplateError as e:
                    raise NotificationTemplateException(e) from e

        # Include the base template into the body, leave subject as-is
        rendered_notification['html_body'] = self.base.render(rendered_notification['html_body'])

        return rendered_notification

    def clean(self):
        pass


class ContentBlock(TranslatableModel):
    base = models.ForeignKey(BaseTemplate, on_delete=models.CASCADE, related_name='content_blocks', editable=False)
    template = models.ForeignKey(
        NotificationTemplate, null=True, blank=True, on_delete=models.CASCADE, related_name='content_blocks',
        verbose_name=_('template'), help_text=_('Do not set if content block is used in multiple templates')
    )
    identifier = models.CharField(max_length=50, verbose_name=_('identifier'))
    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_('name'), max_length=100
        ),
        content=models.TextField(
            verbose_name=_('content'), help_text=_('HTML content for the block'),
        )
    )

    class Meta:
        verbose_name = _('content block')
        verbose_name_plural = _('content blocks')
        unique_together = (('base', 'template', 'identifier'),)

    def __str__(self):
        return self.name
