import io
import hashlib
import requests
import logging

from datetime import timedelta

from django.db import models
from django.utils.translation import pgettext_lazy, gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from sentry_sdk import capture_exception

from aplans.model_images import ModelWithImage


logger = logging.getLogger(__name__)
User = get_user_model()

DEFAULT_AVATAR_SIZE = 360


class Person(ModelWithImage):
    first_name = models.CharField(max_length=100, verbose_name=_('first name'))
    last_name = models.CharField(max_length=100, verbose_name=_('last name'))
    email = models.EmailField(verbose_name=_('email address'))
    title = models.CharField(
        max_length=100, null=True, blank=True,
        verbose_name=pgettext_lazy("person's role", 'title')
    )
    postal_address = models.TextField(max_length=100, verbose_name=_('postal address'), null=True, blank=True)
    organization = models.ForeignKey(
        'django_orghierarchy.Organization', null=True, blank=True, related_name='people',
        on_delete=models.SET_NULL, verbose_name=_('organization'),
        help_text=_('Set if this person is part of an organization')
    )
    user = models.OneToOneField(
        User, null=True, blank=True, related_name='person', on_delete=models.SET_NULL,
        editable=False, verbose_name=_('user'),
        help_text=_('Set if the person has an user account')
    )

    avatar_updated_at = models.DateTimeField(null=True, editable=False)

    class Meta:
        verbose_name = _('person')
        verbose_name_plural = _('people')
        ordering = ('last_name', 'first_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # FIXME: This is hacky
        field = self._meta.get_field('image_cropping')
        field.width = DEFAULT_AVATAR_SIZE
        field.height = DEFAULT_AVATAR_SIZE

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude)
        qs = Person.objects.all()
        if self.email:
            qs = qs.filter(email__iexact=self.email)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({
                'email': _('Person with this email already exists')
            })

    def download_avatar(self):
        url = None
        if self.email.endswith('@hel.fi'):
            url = f'https://api.hel.fi/avatar/{self.email}?s={DEFAULT_AVATAR_SIZE}&d=404'
        else:
            md5_hash = hashlib.md5(self.email.encode('utf8')).hexdigest()
            url = f'https://www.gravatar.com/avatar/{md5_hash}?f=y&s={DEFAULT_AVATAR_SIZE}&d=404'

        try:
            resp = requests.get(url, timeout=5)
        except requests.exceptions.RequestException as err:
            logger.exception('Connection error downloading avatar for %s' % str(self), exc_info=err)
            capture_exception(err)
            return

        # If it's a 404, we accept it as it is and try again sometime
        # later.
        if resp.status_code == 404:
            self.avatar_updated_at = timezone.now()
            self.save(update_fields=['avatar_updated_at'])
            return

        # If it's another error, it might be transient, so we want to try
        # again soon.
        try:
            resp.raise_for_status()
        except Exception as err:
            logger.exception('HTTP error downloading avatar for %s' % str(self), exc_info=err)
            capture_exception(err)
            return

        update_fields = ['avatar_updated_at']
        if not self.image or self.image.read() != resp.content:
            self.image.save('avatar.jpg', io.BytesIO(resp.content))
            update_fields += ['image', 'image_height', 'image_width', 'image_cropping']

        self.avatar_updated_at = timezone.now()
        self.save(update_fields=update_fields)

    def should_update_avatar(self):
        if not self.avatar_updated_at:
            return True
        return (timezone.now() - self.avatar_updated_at) > timedelta(minutes=60)

    def get_avatar_url(self, request):
        return self.get_image_url(request)

    def get_notification_context(self):
        return dict(first_name=self.first_name, last_name=self.last_name)

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)
