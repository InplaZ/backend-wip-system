from django.urls import path
from .views import HealthView, ProductoSearchView, ProductoListCreateView, MovimientoListCreateView, MovimientoDetailView, ReporteIDView, ReporteDiarioView, ImportarCatalogoView
urlpatterns = [
 path('health/', HealthView.as_view()),
 path('productos/', ProductoListCreateView.as_view()),
 path('productos/buscar/', ProductoSearchView.as_view()),
 path('productos/importar-catalogo/', ImportarCatalogoView.as_view()),
 path('movimientos/', MovimientoListCreateView.as_view()),
 path('movimientos/<int:pk>/', MovimientoDetailView.as_view()),
 path('reportes/por-id/', ReporteIDView.as_view()),
 path('reportes/diario/', ReporteDiarioView.as_view()),
]
