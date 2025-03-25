from django.db import models
from django.utils import timezone

class CapacitorData(models.Model):
    adc_value = models.IntegerField()
    estimated_capacity = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Capacitor Reading: {self.adc_value} at {self.timestamp}"

    class Meta:
        verbose_name = "Capacitor Data"
        verbose_name_plural = "Capacitor Data"
        ordering = ['-timestamp']
