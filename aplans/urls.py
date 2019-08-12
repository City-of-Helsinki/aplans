"""aplans URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers
from graphene_django.views import GraphQLView

from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.core import urls as wagtail_urls
from wagtailautocomplete.urls.admin import urlpatterns as autocomplete_admin_urls


from actions.api import all_views as actions_api_views
from indicators.api import all_views as indicators_api_views
from insight.api import all_views as insight_api_views

from users.views import change_admin_plan


router = routers.DefaultRouter()
for view in actions_api_views + indicators_api_views + insight_api_views:
    router.register(view['name'], view['class'], basename=view.get('basename'))


urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/change-admin-plan/', change_admin_plan, name='change-admin-plan'),
    re_path(r'^cms/', include(wagtailadmin_urls)),
    re_path(r'^admin/autocomplete/', include(autocomplete_admin_urls)),
    re_path(r'^documents/', include(wagtaildocs_urls)),
    re_path(r'^pages/', include(wagtail_urls)),
    path('summernote/', include('django_summernote.urls')),
    path('v1/', include(router.urls)),
    path('v1/graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True))),
    path('', include('social_django.urls', namespace='social')),
    path('', include('helusers.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
