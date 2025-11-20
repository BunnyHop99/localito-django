from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReporteViewSet, ReporteGeneradoViewSet

router = DefaultRouter()
router.register(r'analisis', ReporteViewSet, basename='reporte')
router.register(r'generados', ReporteGeneradoViewSet, basename='reporte-generado')

urlpatterns = [
    path('', include(router.urls)),
]