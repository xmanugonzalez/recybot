# Integración Pi 3 / Pi 5

Instalada el 26/10/2026. Pi 3: `smatipitouchpi3@10.199.232.50`.
Pi 5: `recybot@10.199.232.70`.

La Pi 3 captura CSI y sirve la interfaz en http://10.199.232.50:8080.
Tocar el video envía una captura JPEG nueva a YOLOv8n en la Pi 5.
El procesamiento es real, bajo demanda, con un hilo CPU y una solicitud simultánea.
No se ejecuta YOLO en Pi 3. No hay detección automática continua de presencia todavía.

YOLOv8n COCO reconoce objetos, NO las cuatro categorías de material. La API devuelve
`categoria: null`; la interfaz pide selección humana. Una botella no determina plástico
o vidrio. Hace falta entrenar y validar un modelo de residuos antes de automatizar
la clasificación. No se controlan motores ni compuertas.

## Servicios y archivos

Pi 3: `~/recybot-camera/stream_server.py`, `web_bridge.py`, `~/recybot-web`.
Servicios de usuario: `recybot-camera`, `recybot-web`, `recybot-pantalla`.
Pi 5: `~/recybot-ia/server.py`, `.venv`, `modelos/yolov8n.pt`.
Servicio de usuario: `recybot-ia` habilitado; `Linger=yes` confirmado en Pi 5 para
mantenerlo activo sin sesión SSH y permitir el arranque del gestor de usuario al iniciar.

Credencial compartida (no incluir en git): Pi 5 `~/recybot-ia/config/api-token`,
Pi 3 `~/.config/recybot/api-token`, modo 600. El frontend no recibe la credencial.
HTTP es solo para la red local de confianza; no publicar puertos en Internet.
Si cambia IP de Pi 5, ajustar `Environment=RECYBOT_AI_URL=...` en la unidad web de Pi 3
y ejecutar `systemctl --user daemon-reload && systemctl --user restart recybot-web`.

Pi 5 rechaza nuevas inferencias a 80 °C o más; esto no es monitoreo periódico.
La automatización de monitoreo previamente cancelada sigue desactivada.

## Prueba

En Pi 3:
```sh
curl -s -X POST -H 'X-Recybot-Capture: 1' http://127.0.0.1:8080/api/identificar
```
En Pi 5: `.venv/bin/python test_api.py` desde `~/recybot-ia`.

Respaldo anterior de Pi 3: `~/recybot-backup-integracion-20261026/`, con cámara,
unidad web anterior y `web.tar.gz`. No contiene credenciales nuevas.
