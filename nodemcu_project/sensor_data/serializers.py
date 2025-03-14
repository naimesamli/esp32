from rest_framework import serializers
from .models import CapacitorData

class CapacitorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapacitorData
        fields = ['id', 'adc_value', 'estimated_capacity', 'timestamp']
        read_only_fields = ['timestamp']
        def validate_adc_value(self, value):
            if not (0 <= value <= 4095):
                raise serializers.ValidationError("ADC değeri 0 ile 4095 arasında olmalıdır.")
            return value   

