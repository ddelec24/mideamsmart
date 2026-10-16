# Changelog del plugin Midea MSmart

>**IMPORTANT**
>
>Si no hay información sobre la actualización, significa que solo se refiere a la actualización de la documentación, la traducción o el texto.

# 16/10/2026

- Primera versión beta (0.9.0), a probar con aparatos reales: sus comentarios son bienvenidos en el foro
- Creación del plugin: estructura básica, página de configuración y página de equipos
- Instalación de las dependencias: Python 3.13 autónomo (mediante uv) y entorno virtual dedicado al plugin
- Demonio Python (asyncio): inicio, parada limpia, comunicación con Jeedom y transmisión de la lista de equipos
- Sincronización de los aparatos: cuenta MSmartHome, búsqueda en la red local, creación y actualización de los equipos
- Obtención del token y la key, verificados con el aparato, y botón para volver a pedirlos
- Protección contra el bloqueo de la cuenta Midea (códigos 7610 y 65027)
- Dirección de difusión automática por defecto (todas las interfaces de red)
- Control local de los aires acondicionados (AC) y aires acondicionados comerciales (CC) con msmart-ng: estado, consulta periódica, aparato fuera de línea
- Comandos creados según las capacidades de cada aparato, con códigos estables para los escenarios y botón de actualización
- Opciones del equipo: pitido, paso de la consigna, consumo eléctrico
- Control local de los deshumidificadores (A1) con midea-local: modo, ventilación, consigna de humedad, depósito, oscilación, ionizador, bomba, bloqueo infantil, filtro
- Alertas de depósito lleno y de filtro mostradas con un icono verde o rojo
- Ventana de diagnóstico por equipo, con copia de un resumen sin secretos para el foro
- Búsqueda automática en la red local de los aparatos que han cambiado de dirección IP
- Bloqueos de la nube y contraseña rechazada memorizados, incluso tras reiniciar el demonio
- Equipo indicado en timeout cuando el aparato deja de responder, página Salud e información para el foro
