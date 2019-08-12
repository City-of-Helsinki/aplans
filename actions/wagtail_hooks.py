from wagtail.contrib.modeladmin.options import (
    ModelAdmin, modeladmin_register)
from .models import Action


class ActionAdmin(ModelAdmin):
    model = Action
    menu_icon = 'pilcrow'
    menu_order = 100  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ('identifier', 'name',)


modeladmin_register(ActionAdmin)
