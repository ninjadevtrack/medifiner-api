from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .forms import EpidemicForm
from .models import Epidemic
@admin.register(Epidemic)
class EpidemicAdmin(admin.ModelAdmin):

    list_display = (
        '__str__',
        'active',
    )

    fields = ('active', 'content')
    form = EpidemicForm

    def has_add_permission(self, request):
        # check if generally has add permission
        permission = super().has_add_permission(request)
        # set add permission to False, if object already exists
        return not (permission and Epidemic.objects.exists())
