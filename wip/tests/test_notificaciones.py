from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from wip.models import MovimientoWIP, NotificacionWIP, OrdenProducto, RespuestaMovimiento


class FlujoNotificacionesWIPTests(APITestCase):
    def setUp(self):
        User=get_user_model()
        self.origen=User.objects.create_user('origen',password='pass',first_name='Ana',last_name='Origen')
        self.destino=User.objects.create_user('destino',password='pass',first_name='Luis',last_name='Destino')
        self.tercero=User.objects.create_user('tercero',password='pass')
        self.producto=OrdenProducto.objects.create(id_producto='WIP-NOTIF-1',descripcion_referencia='Bolsa prueba')

    def payload(self, **extra):
        data={
            'fecha':'2026-10-20','fecha_inicio':'2026-10-20T15:00:00Z','fecha_fin':None,
            'tipo_movimiento':'TRASPASO','criticidad':'NORMAL','id_producto':self.producto.id_producto,
            'detalle_producto':'Bolsa prueba en extrusión','cantidad_kg':'100.000','ufe':'10.000','scrap_kg':'0',
            'area_origen':'PREPARADO','area_destino':'EXTRUSION','area_posterior':'FLEXOGRAFIA',
            'destinatario_id':self.destino.pk,
            'referencia_ht':'HT-1','codigo_talonario':'T-1','observaciones':'', 'evidencias':[],
            'costo_bs_kg':'2.5000','entregado_por':'No confiar en el cliente','usuario_destino':'tercero',
        }
        data.update(extra)
        return data

    def crear_movimiento(self, key='00000000-0000-0000-0000-000000000001'):
        self.client.force_authenticate(self.origen)
        return self.client.post('/api/movimientos/',self.payload(),format='json',HTTP_IDEMPOTENCY_KEY=key)

    def test_origen_autenticado_y_notificacion_se_guardan_atomicos(self):
        response=self.crear_movimiento()
        self.assertEqual(response.status_code,status.HTTP_201_CREATED,response.data)
        movement=MovimientoWIP.objects.get(pk=response.data['id'])
        self.assertEqual(movement.registrado_por_usuario,self.origen)
        self.assertEqual(movement.registrado_por,self.origen.username)
        self.assertEqual(movement.entregado_por,'Ana Origen')
        self.assertEqual(movement.recibido_por,'Luis Destino')
        self.assertEqual(movement.destinatario,self.destino)
        self.assertEqual(movement.usuario_destino,self.destino.username)
        self.assertEqual(movement.estado_recepcion,'PENDIENTE')
        self.assertIsNotNone(movement.creado_en)
        self.assertEqual(NotificacionWIP.objects.filter(usuario=self.destino,movimiento=movement).count(),1)
        self.assertFalse(NotificacionWIP.objects.filter(usuario=self.tercero,movimiento=movement).exists())
        self.assertEqual(RespuestaMovimiento.objects.filter(movimiento=movement,accion='REGISTRADO').count(),1)

    def test_idempotencia_no_duplica_movimiento_ni_notificacion(self):
        first=self.crear_movimiento()
        second=self.crear_movimiento()
        self.assertEqual(first.status_code,status.HTTP_201_CREATED)
        self.assertEqual(second.status_code,status.HTTP_200_OK)
        self.assertEqual(first.data['id'],second.data['id'])
        self.assertEqual(MovimientoWIP.objects.count(),1)
        self.assertEqual(NotificacionWIP.objects.count(),1)

    def test_solo_destinatario_responde_y_origen_recibe_notificacion(self):
        created=self.crear_movimiento()
        movement_id=created.data['id']
        self.client.force_authenticate(self.tercero)
        self.assertEqual(self.client.post(f'/api/movimientos/{movement_id}/responder/',{'estado':'ACEPTADO'},format='json').status_code,status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.destino)
        response=self.client.post(f'/api/movimientos/{movement_id}/responder/',{'estado':'ACEPTADO'},format='json')
        self.assertEqual(response.status_code,status.HTTP_200_OK,response.data)
        movement=MovimientoWIP.objects.get(pk=movement_id)
        self.assertEqual(movement.estado_recepcion,'ACEPTADO')
        self.assertEqual(movement.respondido_por_usuario,self.destino)
        self.assertIsNotNone(movement.fecha_respuesta)
        self.assertEqual(NotificacionWIP.objects.filter(usuario=self.origen,movimiento=movement,tipo='RESPUESTA_MOVIMIENTO').count(),1)
        duplicate=self.client.post(f'/api/movimientos/{movement_id}/responder/',{'estado':'RECHAZADO','comentario':'Cambio posterior'},format='json')
        self.assertEqual(duplicate.status_code,status.HTTP_400_BAD_REQUEST)

    def test_observar_exige_motivo_y_origen_puede_reabrir_sin_borrar_historial(self):
        created=self.crear_movimiento();movement_id=created.data['id']
        self.client.force_authenticate(self.destino)
        invalid=self.client.post(f'/api/movimientos/{movement_id}/responder/',{'estado':'OBSERVADO','comentario':'  '},format='json')
        self.assertEqual(invalid.status_code,status.HTTP_400_BAD_REQUEST)
        observed=self.client.post(f'/api/movimientos/{movement_id}/responder/',{'estado':'OBSERVADO','comentario':'El peso no coincide'},format='json')
        self.assertEqual(observed.status_code,status.HTTP_200_OK,observed.data)
        self.assertEqual(MovimientoWIP.objects.get(pk=movement_id).estado_recepcion,'OBSERVADO')
        self.client.force_authenticate(self.origen)
        reopened=self.client.post(f'/api/movimientos/{movement_id}/reabrir/',{'comentario':'Se adjunta pesaje corregido'},format='json')
        self.assertEqual(reopened.status_code,status.HTTP_200_OK,reopened.data)
        self.assertEqual(MovimientoWIP.objects.get(pk=movement_id).estado_recepcion,'PENDIENTE')
        self.assertEqual(list(RespuestaMovimiento.objects.filter(movimiento_id=movement_id).values_list('accion',flat=True)),['REGISTRADO','OBSERVADO','REABIERTO'])
        self.assertTrue(NotificacionWIP.objects.filter(usuario=self.destino,movimiento_id=movement_id,tipo='MOVIMIENTO_REABIERTO').exists())

    def test_rechazo_conserva_motivo_y_notifica_origen(self):
        created=self.crear_movimiento();movement_id=created.data['id']
        self.client.force_authenticate(self.destino)
        invalid=self.client.post(f'/api/movimientos/{movement_id}/responder/',{'estado':'RECHAZADO'},format='json')
        self.assertEqual(invalid.status_code,status.HTTP_400_BAD_REQUEST)
        rejected=self.client.post(f'/api/movimientos/{movement_id}/responder/',{'estado':'RECHAZADO','comentario':'Empaque dañado'},format='json')
        self.assertEqual(rejected.status_code,status.HTTP_200_OK,rejected.data)
        self.assertEqual(MovimientoWIP.objects.get(pk=movement_id).respuesta_recepcion,'Empaque dañado')
        self.assertTrue(NotificacionWIP.objects.filter(usuario=self.origen,movimiento_id=movement_id).exists())

    def test_listado_y_lectura_de_notificaciones_solo_pertenecen_al_usuario(self):
        created=self.crear_movimiento();notification=NotificacionWIP.objects.get(movimiento_id=created.data['id'],usuario=self.destino)
        self.client.force_authenticate(self.tercero)
        self.assertEqual(self.client.get('/api/movimientos/').data['count'],0)
        self.assertEqual(self.client.get(f"/api/movimientos/{created.data['id']}/").status_code,status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get('/api/notificaciones/').data['count'],0)
        self.assertEqual(self.client.post(f'/api/notificaciones/{notification.pk}/leer/').status_code,status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.destino)
        self.assertEqual(self.client.get('/api/movimientos/').data['count'],1)
        self.assertEqual(self.client.get('/api/notificaciones/?no_leidas=true').data['count'],1)
        read=self.client.post(f'/api/notificaciones/{notification.pk}/leer/')
        self.assertEqual(read.status_code,status.HTTP_200_OK)
        self.assertFalse(read.data['no_leida'])
        self.assertEqual(self.client.get('/api/notificaciones/?no_leidas=true').data['count'],0)

    def test_lista_destinatarios_solo_incluye_usuarios_activos_que_no_sean_el_origen(self):
        inactive=get_user_model().objects.create_user('inactivo',password='pass',is_active=False)
        self.client.force_authenticate(self.origen)
        response=self.client.get('/api/usuarios/destinatarios/')
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        ids={row['id'] for row in response.data}
        self.assertIn(self.destino.pk,ids)
        self.assertNotIn(self.origen.pk,ids)
        self.assertNotIn(inactive.pk,ids)
