from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CapacitorDataViewSet,
    receive_measurement,
    dashboard,
    start_serial_collection,
    start_random_collection,
)

router = DefaultRouter()
router.register(r'capacitor-data', CapacitorDataViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/receive/', receive_measurement, name='receive_measurement'),
    path('api/start-serial/', start_serial_collection, name='start_serial'),
    path('', dashboard, name='dashboard'),
    path('api/start-random/', start_random_collection, name='start_random'),
]