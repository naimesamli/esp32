from django.contrib import admin
from .models import CapacitorData

@admin.register(CapacitorData)
class CapacitorDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'adc_value', 'estimated_capacity', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('adc_value', 'estimated_capacity')
    date_hierarchy = 'timestamp'