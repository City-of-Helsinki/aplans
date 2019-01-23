from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ('first_name', 'last_name', 'email')
