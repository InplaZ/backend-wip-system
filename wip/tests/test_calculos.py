from datetime import date
from decimal import Decimal
from django.test import TestCase
from wip.models import OrdenProducto, MovimientoWIP

class MovimientoCalculadoTests(TestCase):
    def setUp(self):
        self.producto = OrdenProducto.objects.create(id_producto='TEST-1', descripcion_referencia='Producto de prueba')
    def crear(self, tipo):
        return MovimientoWIP.objects.create(fecha=date(2026,9,1),tipo_movimiento=tipo,producto=self.producto,detalle_producto='Detalle',cantidad_kg=Decimal('10'),ufe=Decimal('2'),scrap_kg=Decimal('1'),area_origen='EXTRUSION',area_destino='ALMACEN',entregado_por='A',recibido_por='B',costo_bs_kg=Decimal('2.5'))
    def test_ingreso_calcula_signos_y_costo(self):
        m=self.crear('INGRESO'); self.assertEqual(m.ufe_calculada,Decimal('2')); self.assertEqual(m.movimiento_almacen,Decimal('10')); self.assertEqual(m.costo_total_bs,Decimal('25.0'))
    def test_salida_calcula_signos(self):
        m=self.crear('SALIDA'); self.assertEqual(m.ufe_calculada,Decimal('-2')); self.assertEqual(m.movimiento_almacen,Decimal('-10'))
    def test_traspaso_no_afecta_total_calculado_excel(self):
        m=self.crear('TRASPASO'); self.assertEqual(m.ufe_calculada,Decimal('0')); self.assertEqual(m.movimiento_almacen,Decimal('0'))
