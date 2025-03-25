from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import user_login, user_logout
from .views import (
    CapacitorDataViewSet,
    receive_measurement,
    dashboard,
    user_register,
    home,
    start_serial_collection,
    start_random_collection,
    stop_random_collection,
    control_data,
    check_status,
)

router = DefaultRouter()
router.register(r'capacitor-data', CapacitorDataViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/receive/', receive_measurement, name='receive_measurement'),
    path('api/start-serial/', start_serial_collection, name='start_serial'),
    path('dashboard', dashboard, name='dashboard'),
    path('', home, name='home'),  # Ana sayfa
    path('login/', user_login, name='login'),  # Giriş sayfası
    path('logout/', user_logout, name='logout'),  # Çıkış yapma
    path('register/', user_register, name='register'),  # Kayıt sayfası
    path('api/control/', control_data, name='control_data'),
    path('api/start-random/', start_random_collection, name='start_random'),
    path('api/stop-random/', stop_random_collection, name='stop_random'),
    path('api/status/', check_status, name='check_status'),
]