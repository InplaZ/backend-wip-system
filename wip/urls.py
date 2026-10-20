from django.urls import path
from .views import (HealthView, UsuarioActualView, UsuarioDestinatarioListView,
    ProductoSearchView, ProductoListCreateView, MovimientoListCreateView,
    MovimientoDetailView, ResponderMovimientoView, ReabrirMovimientoView,
    NotificacionListView, NotificacionLeerView, ReporteIDView,
    ReporteDiarioView, ImportarCatalogoView)
urlpatterns = [
 path('health/', HealthView.as_view()),
 path('usuario/actual/', UsuarioActualView.as_view()),
 path('usuarios/destinatarios/', UsuarioDestinatarioListView.as_view()),
 path('notificaciones/', NotificacionListView.as_view()),
 path('notificaciones/<int:pk>/leer/', NotificacionLeerView.as_view()),
 path('productos/', ProductoListCreateView.as_view()),
 path('productos/buscar/', ProductoSearchView.as_view()),
 path('productos/importar-catalogo/', ImportarCatalogoView.as_view()),
 path('movimientos/', MovimientoListCreateView.as_view()),
 path('movimientos/<int:pk>/', MovimientoDetailView.as_view()),
 path('movimientos/<int:pk>/responder/', ResponderMovimientoView.as_view()),
 path('movimientos/<int:pk>/reabrir/', ReabrirMovimientoView.as_view()),
 path('reportes/por-id/', ReporteIDView.as_view()),
 path('reportes/diario/', ReporteDiarioView.as_view()),
]
