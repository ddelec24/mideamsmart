# Plugin Midea MSmart

> **Plugin en desarrollo**: esta documentación describe el estado actual del plugin y se completará en cada versión.

## Presentación

El plugin **Midea MSmart** permite controlar **en local** los aires acondicionados y deshumidificadores Midea y de marcas asociadas (Comfee, Inventor, Qlima…) compatibles con la aplicación **MSmartHome**.

La cuenta MSmartHome solo sirve para:

- listar los aparatos asociados a la cuenta;
- obtener una sola vez las claves de autenticación (*token* y *key*) de los aparatos recientes (protocolo V3).

Después, todos los comandos y lecturas de estado pasan directamente por la red local, sin la nube de Midea.

Aparatos compatibles:

| Tipo | Aparato |
|---|---|
| `0xAC` | Aire acondicionado (split, portátil, PortaSplit…) |
| `0xCC` | Aire acondicionado comercial |
| `0xA1` | Deshumidificador |

## Requisitos previos

- Jeedom 4.5 o superior, en Debian 12 o 13.
- Los aparatos y Jeedom deben estar en la **misma red local** (misma subred) para que funcione la detección.
- Una cuenta **MSmartHome** en la que los aparatos estén **vinculados directamente**. Un aparato solo *compartido* desde otra cuenta no permite obtener sus claves.

> **Consejo**
>
> Use preferentemente una contraseña compuesta solo de letras y cifras.
> Tras varios intentos de conexión fallidos, la nube de Midea bloquea temporalmente la cuenta, desde unos minutos hasta 24 horas (errores `7610` o `65027`). En ese caso, espere antes de volver a intentarlo.

## Configuración del plugin

Tras la instalación, active el plugin y lance la instalación de las dependencias. El plugin instala su propio entorno Python, aislado del sistema.

### Dependencias

La instalación de las dependencias, lanzada desde la página de configuración del plugin, instala únicamente en la carpeta del plugin:

- un **Python 3.13** autónomo, descargado con la herramienta [uv](https://github.com/astral-sh/uv), independientemente de la versión de Python del sistema;
- un entorno virtual (`resources/python_venv`) con las bibliotecas del plugin, en versiones fijadas y verificadas por huella.

La instalación tarda unos minutos y ocupa unos 130 MB. En un sistema de 32 bits (Raspberry Pi en `armhf`), también se instala un compilador y la operación es más larga, ya que una biblioteca debe compilarse.

Tras una actualización del plugin que cambie estas versiones, las dependencias vuelven al estado *NOK*: basta con relanzar su instalación. No se incluyen en las copias de seguridad de Jeedom; tras una restauración, relance su instalación.

### Parámetros

![Configuración del plugin](../images/plugin_config.png)

- **Cuenta MSmartHome**
  - **Usuario (email)** y **Contraseña** de la cuenta MSmartHome.
- **Red local**
  - **Dirección de difusión**: dirección(es) de broadcast usada(s) para descubrir los aparatos, separadas por comas. Déjelo vacío (por defecto) para difundir en todas las interfaces de red de Jeedom. Si no se encuentran los aparatos, indique la dirección de broadcast de su red (por ejemplo `192.168.1.255`).
  - **Intervalo de consulta por defecto**: tiempo en segundos entre dos lecturas del estado de los aparatos (30 s por defecto, 10 s como mínimo).
- **Demonio**
  - **Puerto del demonio**: puerto local usado por el demonio (55114 por defecto). Modifíquelo solo en caso de conflicto con otro plugin.

### Demonio

El demonio gestiona la comunicación local con los aparatos. Una vez instaladas las dependencias, se inicia automáticamente (gestión automática activada), o con el botón **(Re)Iniciar** de la página de configuración del plugin.

- Solo escucha en la máquina Jeedom (`127.0.0.1`), en el puerto definido arriba.
- **Nunca** se conecta a la nube de Midea al iniciarse, lo que evita los bloqueos de la cuenta.
- Sus mensajes están en el log `mideamsmart_daemon`, los de la instalación de las dependencias en `mideamsmart_update`. Ponga el nivel de log del plugin en *Debug* para obtener el detalle de los intercambios. El plugin oculta en ellos las contraseñas, el *token* y la *key*.

## Añadir aparatos

En la página del plugin, el botón **Sincronizar** (el demonio debe estar iniciado):

1. busca los aparatos en la red local;
2. si hay una cuenta MSmartHome configurada, se conecta a ella y obtiene la lista de aparatos de la cuenta;
3. para cada aparato V3 cuyas claves aún no se conocen, obtiene el *token* y la *key* desde la nube y luego **los verifica directamente con el aparato** antes de guardarlos;
4. crea los nuevos equipos, o actualiza la dirección IP, el puerto y el protocolo de los existentes. Los nombres y las claves ya presentes nunca se modifican.

Un mensaje resume la operación e indica los aparatos cuyas claves no se han podido obtener. Los aparatos de un tipo no compatible se ignoran. Sin cuenta MSmartHome, solo se realiza la búsqueda local.

![Página del plugin](../images/plugin_devices.png)

El botón **Añadir** permite crear un equipo manualmente, por ejemplo para un aparato situado en otra subred. En ese caso, debe indicar usted mismo el identificador, la dirección IP y, para un aparato V3, el *token* y la *key*.

## Equipo

![Equipo](../images/device_config.png)

- **Aparato Midea**
  - **Tipo de aparato**: aire acondicionado, aire acondicionado comercial o deshumidificador.
  - **Identificador del aparato**: identificador Midea, rellenado automáticamente durante la sincronización.
- **Conexión local**
  - **Dirección IP** y **Puerto** (6444 por defecto).
  - **Versión del protocolo**: V3 para la mayoría de los aparatos recientes, V2 para los más antiguos.
  - **Token** y **Key**: claves de autenticación de los aparatos V3, obtenidas automáticamente.
  - **Obtener token/key desde la nube**: vuelve a pedir a la nube las claves de este aparato y las verifica, por ejemplo tras reiniciar el módulo Wi-Fi. Guarde el equipo antes de usarlo.
- **Opciones**
  - **Intervalo de consulta**: déjelo vacío para usar el valor de la configuración del plugin.
  - **Pitido de confirmación**: el aparato emite un pitido con cada comando recibido.
  - **Paso de la consigna** (aires acondicionados): 1 °C o 0,5 °C.
  - **Consumo eléctrico** (aires acondicionados): crea los comandos de potencia y consumo. Si los valores son incoherentes, cambie el **formato** (BCD o binario) o el **factor de escala**.
- **Información**
  - Número de serie y modelo del aparato, en solo lectura.

> **Importante**
>
> Guarde el *token* y la *key* de sus aparatos V3 en un lugar seguro. Permiten seguir controlando los aparatos aunque la nube de Midea deje de estar disponible.

## Comandos

Los comandos se crean automáticamente **según las capacidades que comunica cada aparato**, en cuanto responde por primera vez. Si el aparato no devuelve sus capacidades, se usan capacidades por defecto y la petición se repite cada 10 minutos.

Los comandos info de tipo texto contienen un **código estable**, independiente del idioma (por ejemplo `cool`): use estos códigos en sus escenarios. Los comandos action asociados ofrecen etiquetas traducidas. Las infos ya mostradas por una acción vinculada se ocultan por defecto.

El botón **Actualizar los comandos** de la pestaña *Comandos* añade los comandos que faltan, elimina los de las funciones que el aparato ya no declara y vuelve a leer sus capacidades. Se conservan los nombres y ajustes de sus comandos existentes.

| Identificador lógico | Aparatos | Contenido |
|---|---|---|
| `power`, `on`, `off` | AC, CC, A1 | Estado (0/1), encender, apagar |
| `mode`, `setMode` | AC, CC | Modo: `auto`, `cool`, `dry`, `smart_dry`, `heat`, `fan_only` (CC: `fan`). Elegir un modo enciende el aparato |
| `targetTemperature`, `setTargetTemperature` | AC, CC | Consigna en °C, con los límites del aparato y el paso elegido en el equipo |
| `indoorTemperature`, `outdoorTemperature` | AC, CC | Temperaturas interior y exterior |
| `fanSpeed`, `setFanSpeed` | AC, CC | Ventilación: `auto`, `silent`, `low`, `medium`, `high`, `max`, `custom` (CC: `l1` a `l7`, `auto`) |
| `fanSpeedPercent`, `setFanSpeedPercent` | AC | Velocidad libre de 1 a 100 %, si el aparato la admite |
| `swingMode`, `setSwingMode` | AC, CC | Oscilación: `off`, `vertical`, `horizontal`, `both` |
| `horizontalSwingAngle`, `verticalSwingAngle` + `set…` | AC, CC | Posición de las lamas: `off`/`close`, `pos_1` a `pos_5`, `auto` |
| `preset`, `setPreset` | AC, CC | Preajuste exclusivo: `none`, `sleep`, `freeze_protection`, `eco`, `ieco`, `turbo` (CC: `none`, `eco`, `silent`, `sleep`) |
| `breezeMode`, `setBreezeMode` | AC | Modo Breeze: `off`, `breeze_away`, `breeze_mild`, `breezeless` |
| `indoorHumidity`, `targetHumidity`, `setTargetHumidity` | AC, CC | Humedad interior y consigna de humedad (%) |
| `displayOn`, `toggleDisplay` | AC | Estado de la pantalla y conmutación |
| `purifier`, `purifierOn`, `purifierOff` / `purifierMode`, `setPurifierMode` | AC / CC | Purificador (AC: encendido/apagado; CC: `off`, `on`, `auto`) |
| `flash`, `outSilent`, `cascadeMode`, `freshAirFanSpeed`, `rateSelect`, `auxMode` + actions | AC (CC : `auxMode`) | Funciones avanzadas, según el modelo |
| `selfCleanActive`, `startSelfClean`, `filterAlert`, `defrostActive`, `errorCode` | AC | Autolimpieza, alerta de filtro, desescarche, código de error |
| `realTimePower`, `currentEnergy`, `totalEnergy` | AC | Potencia (W) y consumos (kWh), si la opción *Consumo eléctrico* está marcada |
| `mode`, `setMode` | A1 | Modo: `manual`, `continuous`, `auto`, `clothes_dry`, `shoes_dry`, `silent`. Elegir un modo enciende el aparato |
| `fanSpeed`, `setFanSpeed` | A1 | Ventilación: `lowest`, `low`, `medium`, `high`, `auto` |
| `currentHumidity`, `currentTemperature`, `targetHumidity`, `setTargetHumidity` | A1 | Humedad y temperatura ambiente, consigna de humedad de 35 a 85 % |
| `tankLevel`, `tankFull`, `waterLevelSet`, `setWaterLevelSet` | A1 | Nivel del depósito (%), depósito lleno, umbral del depósito (`25`, `50`, `75`, `100`) |
| `swing`, `childLock`, `anion`, `pump` + `…On`, `…Off` | A1 | Oscilación, bloqueo infantil, ionizador, bomba (si el aparato tiene una) |
| `filterCleaningReminder`, `resetFilter` | A1 | Aviso de limpieza del filtro y su restablecimiento |
| `online`, `refresh` | AC, CC, A1 | Aparato accesible (0/1) y actualización inmediata |

## Solución de problemas

| Mensaje | Solución |
|---|---|
| *Usuario o contraseña de MSmartHome incorrectos* | Compruebe la cuenta en la configuración del plugin. El plugin no lo vuelve a intentar mientras no cambien las credenciales. |
| *La nube de Midea ha bloqueado temporalmente la cuenta* | Demasiadas conexiones (códigos `7610`, `65027`). Espere el tiempo indicado sin lanzar otra sincronización. |
| *aparato no vinculado directamente a esta cuenta (¿compartido?)* | En la aplicación MSmartHome, vincule el aparato a esta cuenta, no solo mediante un uso compartido. |
| *aparato ausente de la cuenta MSmartHome* | El aparato está en la red pero en otra cuenta: introduzca *token* y *key* manualmente, o vincúlelo a esta cuenta. |
| *claves rechazadas por el aparato* | Vuelva a lanzar **Obtener token/key desde la nube**; si el problema persiste, vuelva a vincular el aparato en la aplicación. |
| *aparato no encontrado en la red local* / *inaccesible* | Compruebe que el aparato está encendido y en la misma red que Jeedom, o indique la **dirección de difusión** de su red. |

## Créditos

El plugin se basa en las bibliotecas de código abierto [msmart-ng](https://github.com/mill1000/midea-msmart) y [midea-local](https://github.com/midea-lan/midea-local).
