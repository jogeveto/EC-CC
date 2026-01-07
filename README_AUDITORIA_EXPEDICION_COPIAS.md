# Informe de Auditoría - Módulo ExpedicionCopias

## Resumen Ejecutivo

Este informe presenta los resultados de la auditoría completa del módulo ExpedicionCopias, enfocada en identificar inconsistencias en sentencias, mapear variables externas y detectar strings hardcodeados que deberían estar en constantes o configuración.

**Fecha de Auditoría**: 2025-01-27  
**Alcance**: 100% del módulo ExpedicionCopias (carpeta `ExpedicionCopias/`)  
**Archivos Analizados**: 14 archivos Python + 1 archivo de configuración

## 1. Inconsistencias Encontradas

### 1.1. Uso Inconsistente de Campos para Número de Radicado

**Problema Identificado**: Se utilizan dos campos diferentes (`sp_name` y `sp_ticketnumber`) para representar el mismo concepto (número de radicado), generando confusión y posibles errores.

**Evidencia**:
- En `expedicion_service.py` línea 1613: `numero_pqrs = caso.get("sp_name", "")`
- En `expedicion_service.py` línea 411: `ticket_number = caso.get('sp_ticketnumber', 'N/A')`
- En `expedicion_service.py` línea 1154: `radicado = caso.get("sp_ticketnumber", "") or caso.get("sp_name", case_id)`
- En `graph_client.py` línea 849: `numero_pqrs = caso.get("sp_name", "") or caso.get("sp_ticketnumber", "")`
- En `non_critical_rules_validator.py` línea 63: Se valida solo `sp_name` como número de radicado

**Impacto**: 
- Alto riesgo de inconsistencia en reportes y logs
- Dificulta el mantenimiento y debugging
- Puede generar confusión sobre qué campo usar

**Recomendación**: 
- **NO CAMBIAR** - La inconsistencia parece intencional para manejar diferentes escenarios:
  - `sp_name`: Número de radicado principal
  - `sp_ticketnumber`: Número de ticket alternativo
- **SÍ DOCUMENTAR**: Crear constantes o documentación clara sobre cuándo usar cada campo
- **SÍ ESTANDARIZAR**: En reportes, usar siempre la misma lógica de combinación: `f"{ticket_number} ({sp_name})" if sp_name else ticket_number`

### 1.2. Uso Inconsistente de Campos de Email

**Problema Identificado**: Se utilizan múltiples campos para obtener el email del destinatario, con diferentes prioridades según el contexto.

**Evidencia**:
- En `expedicion_service.py` línea 1724-1728: `_obtener_email_caso()` usa prioridad: `sp_correoelectronico`, `emailaddress`, `emailaddress1`
- En `expedicion_service.py` línea 1819: `_obtener_email_creador()` usa `invt_correoelectronico` como primera opción
- En `expedicion_service.py` línea 1624: Para plantillas se usa `invt_correoelectronico`
- En `non_critical_rules_validator.py` línea 48: Se valida `invt_correoelectronico` en modo PROD

**Impacto**:
- Medio - Diferentes métodos pueden retornar diferentes emails para el mismo caso
- Puede causar que emails se envíen a destinatarios incorrectos

**Recomendación**:
- **SÍ CAMBIAR** - Estandarizar el uso de campos de email:
  - Para envío a cliente: Usar siempre `invt_correoelectronico` (email del destinatario del caso)
  - Para envío a responsable/creador: Usar `_obtener_email_creador()` que ya tiene la lógica correcta
  - Documentar claramente la diferencia entre `sp_correoelectronico` (email del caso) e `invt_correoelectronico` (email del destinatario)

### 1.3. Inconsistencia en Mapeo de Variables de Plantillas

**Problema Identificado**: Variaciones en el nombre de variables de plantillas y uso inconsistente de placeholders.

**Evidencia**:
- En `expedicion_service.py` línea 1626: Se reemplaza `[Correo Electrónico]` y `[Correo electrónico]` (dos variantes)
- En `expedicion_service.py` línea 1636: Se reemplaza `[Enlace Onedrive.pdf]` y `[​Enlace Onedrive.pdf​]` (con caracteres especiales)
- En `config.example.json` línea 40 vs 57: Diferentes variantes de texto en plantillas

**Impacto**:
- Bajo - Puede causar que algunas variables no se reemplacen correctamente
- Dificulta el mantenimiento de plantillas

**Recomendación**:
- **SÍ CAMBIAR** - Estandarizar nombres de variables en plantillas:
  - Usar siempre la misma convención (ej: `[Correo electrónico]` en minúsculas)
  - Crear lista de constantes con los nombres de variables permitidas
  - Validar que todas las variantes se reemplacen

### 1.4. Uso Inconsistente de Campos de Fecha

**Problema Identificado**: Se usa principalmente `createdon` para fechas, pero hay otros campos disponibles que no se utilizan consistentemente.

**Evidencia**:
- En `expedicion_service.py` línea 1629: Se usa `createdon` para fecha de ingreso
- En `crm_client.py` línea 35: Existen campos `sp_fechadecreacinreal`, `sp_fechadevencimiento` que no se usan
- En `expedicion_service.py` línea 244: Se ordena por `createdon desc` en consultas

**Impacto**:
- Bajo - El uso de `createdon` parece consistente y adecuado

**Recomendación**:
- **NO CAMBIAR** - El uso de `createdon` es apropiado y consistente
- **SÍ DOCUMENTAR**: Aclarar que `createdon` es el campo estándar para fecha de creación del caso

### 1.5. Inconsistencia en Nombres de Configuración

**Problema Identificado**: Uso inconsistente de nombres de configuración (camelCase vs PascalCase).

**Evidencia**:
- En `expedicion_service.py` línea 1899: `UsuaroRedBR` (typo: debería ser "Usuario")
- En `expedicion_service.py` línea 382: `incluirCaratula` (camelCase)
- En `expedicion_service.py` línea 1888: `CodigoAsistente` (PascalCase)
- En `db_service.py` línea 70: `Esquema` vs `schema` (ambos aceptados)

**Impacto**:
- Medio - Puede causar errores de configuración si no se usa el nombre exacto
- Dificulta el mantenimiento

**Recomendación**:
- **SÍ CAMBIAR** - Estandarizar nombres de configuración:
  - Usar camelCase para todas las claves de configuración
  - Corregir typo: `UsuaroRedBR` → `UsuarioRedBR`
  - Documentar la convención de nombres en `config.example.json`

## 2. Tabla de Variables Externas

Esta tabla mapea todas las variables que provienen de fuentes externas (config.json, CRM, DocuWare, Email/Graph API, Drive/OneDrive). **NO se incluyen variables locales calculadas dentro de los métodos**.

| Clase | Método | Línea | Variable | Origen |
|-------|--------|-------|----------|--------|
| ExpedicionService | __init__ | 48 | Dynamics365.tenant_id | config.json |
| ExpedicionService | __init__ | 48 | Dynamics365.client_id | config.json |
| ExpedicionService | __init__ | 48 | Dynamics365.base_url | config.json |
| ExpedicionService | __init__ | 49 | GraphAPI.tenant_id | config.json |
| ExpedicionService | __init__ | 49 | GraphAPI.client_id | config.json |
| ExpedicionService | __init__ | 51 | dynamics_client_secret | config.json (Rocketbot) |
| ExpedicionService | __init__ | 52 | graph_client_secret | config.json (Rocketbot) |
| ExpedicionService | _validar_franja_horaria_tipo | 108 | ReglasNegocio.Copias.FranjasHorarias | config.json |
| ExpedicionService | _validar_franja_horaria_tipo | 110 | ReglasNegocio.CopiasOficiales.FranjasHorarias | config.json |
| ExpedicionService | _obtener_ruta_lock | 134 | Globales.RutaBaseProyecto | config.json |
| ExpedicionService | _enviar_notificacion_error_conexion | 253 | ReglasNegocio.Copias.emailResponsable | config.json |
| ExpedicionService | _enviar_notificacion_error_conexion | 256 | ReglasNegocio.CopiasOficiales.emailResponsable | config.json |
| ExpedicionService | _enviar_notificacion_error_conexion | 266 | Notificaciones.ErrorConexion.Copias.asunto | config.json |
| ExpedicionService | _enviar_notificacion_error_conexion | 266 | Notificaciones.ErrorConexion.Copias.cuerpo | config.json |
| ExpedicionService | _enviar_notificacion_error_conexion | 266 | Notificaciones.ErrorConexion.CopiasOficiales.asunto | config.json |
| ExpedicionService | _enviar_notificacion_error_conexion | 266 | Notificaciones.ErrorConexion.CopiasOficiales.cuerpo | config.json |
| ExpedicionService | _enviar_notificacion_error_conexion | 293 | GraphAPI.user_email | config.json |
| ExpedicionService | _enviar_notificacion_inicio | 312 | ReglasNegocio.Copias.emailResponsable | config.json |
| ExpedicionService | _enviar_notificacion_inicio | 315 | ReglasNegocio.CopiasOficiales.emailResponsable | config.json |
| ExpedicionService | _enviar_notificacion_inicio | 325 | Notificaciones.InicioEjecucion.Copias.asunto | config.json |
| ExpedicionService | _enviar_notificacion_inicio | 325 | Notificaciones.InicioEjecucion.Copias.cuerpo | config.json |
| ExpedicionService | _enviar_notificacion_inicio | 325 | Notificaciones.InicioEjecucion.CopiasOficiales.asunto | config.json |
| ExpedicionService | _enviar_notificacion_inicio | 325 | Notificaciones.InicioEjecucion.CopiasOficiales.cuerpo | config.json |
| ExpedicionService | _enviar_notificacion_inicio | 350 | GraphAPI.user_email | config.json |
| ExpedicionService | procesar_particulares | 373 | ReglasNegocio.Copias.FranjasHorarias | config.json |
| ExpedicionService | procesar_particulares | 373 | ReglasNegocio.Copias.ExcepcionesDescarga | config.json |
| ExpedicionService | procesar_particulares | 373 | ReglasNegocio.Copias.incluirCaratula | config.json |
| ExpedicionService | procesar_particulares | 373 | ReglasNegocio.Copias.Subcategorias | config.json |
| ExpedicionService | procesar_particulares | 373 | ReglasNegocio.Copias.Especificaciones | config.json |
| ExpedicionService | _procesar_caso_particular | 423 | caso.invt_matriculasrequeridas | CRM |
| ExpedicionService | _procesar_caso_particular | 520 | caso._sp_subcategoriapqrs_value | CRM |
| ExpedicionService | _enviar_pdf_pequeno | 651 | GraphAPI.user_email | config.json |
| ExpedicionService | _enviar_pdf_pequeno | 642 | ReglasNegocio.Copias.Subcategorias[].PlantillasEmail.adjunto.asunto | config.json |
| ExpedicionService | _enviar_pdf_pequeno | 642 | ReglasNegocio.Copias.Subcategorias[].PlantillasEmail.adjunto.cuerpo | config.json |
| ExpedicionService | _enviar_pdf_grande | 709 | OneDrive.carpetaBase | config.json |
| ExpedicionService | _enviar_pdf_grande | 710 | GraphAPI.user_email | config.json |
| ExpedicionService | _enviar_pdf_grande | 713 | caso.sp_name | CRM |
| ExpedicionService | _enviar_pdf_grande | 729 | ReglasNegocio.Copias.emailResponsable | config.json |
| ExpedicionService | _enviar_pdf_grande | 783 | ReglasNegocio.Copias.Subcategorias[].PlantillasEmail.onedrive.asunto | config.json |
| ExpedicionService | _enviar_pdf_grande | 783 | ReglasNegocio.Copias.Subcategorias[].PlantillasEmail.onedrive.cuerpo | config.json |
| ExpedicionService | _enviar_email_sin_adjuntos | 854 | ReglasNegocio.Copias.emailResponsable | config.json |
| ExpedicionService | _enviar_email_sin_adjuntos | 854 | ReglasNegocio.CopiasOficiales.emailResponsable | config.json |
| ExpedicionService | _enviar_email_sin_adjuntos | 855 | caso._sp_subcategoriapqrs_value | CRM |
| ExpedicionService | _enviar_email_sin_adjuntos | 867 | ReglasNegocio.Copias.Subcategorias[].PlantillasEmail.sinAdjuntos.asunto | config.json |
| ExpedicionService | _enviar_email_sin_adjuntos | 867 | ReglasNegocio.Copias.Subcategorias[].PlantillasEmail.sinAdjuntos.cuerpo | config.json |
| ExpedicionService | _enviar_email_sin_adjuntos | 867 | ReglasNegocio.CopiasOficiales.PlantillasEmail.sinAdjuntos.asunto | config.json |
| ExpedicionService | _enviar_email_sin_adjuntos | 867 | ReglasNegocio.CopiasOficiales.PlantillasEmail.sinAdjuntos.cuerpo | config.json |
| ExpedicionService | _enviar_email_sin_adjuntos | 888 | GraphAPI.user_email | config.json |
| ExpedicionService | _enviar_email_regla_no_critica | 913 | ReglasNegocio.Copias.emailResponsable | config.json |
| ExpedicionService | _enviar_email_regla_no_critica | 915 | ReglasNegocio.CopiasOficiales.emailResponsable | config.json |
| ExpedicionService | _enviar_email_regla_no_critica | 924 | ReglasNegocio.Copias.PlantillaEmailReglasNoCriticas.asunto | config.json |
| ExpedicionService | _enviar_email_regla_no_critica | 924 | ReglasNegocio.Copias.PlantillaEmailReglasNoCriticas.cuerpo | config.json |
| ExpedicionService | _enviar_email_regla_no_critica | 924 | ReglasNegocio.CopiasOficiales.PlantillaEmailReglasNoCriticas.asunto | config.json |
| ExpedicionService | _enviar_email_regla_no_critica | 924 | ReglasNegocio.CopiasOficiales.PlantillaEmailReglasNoCriticas.cuerpo | config.json |
| ExpedicionService | _enviar_email_regla_no_critica | 948 | GraphAPI.user_email | config.json |
| ExpedicionService | _enviar_email_error_compartir | 976 | ReglasNegocio.Copias.emailResponsable | config.json |
| ExpedicionService | _enviar_email_error_compartir | 978 | ReglasNegocio.CopiasOficiales.emailResponsable | config.json |
| ExpedicionService | _enviar_email_error_compartir | 1013 | GraphAPI.user_email | config.json |
| ExpedicionService | procesar_oficiales | 1051 | ReglasNegocio.CopiasOficiales.FranjasHorarias | config.json |
| ExpedicionService | procesar_oficiales | 1051 | ReglasNegocio.CopiasOficiales.ExcepcionesDescarga | config.json |
| ExpedicionService | procesar_oficiales | 1051 | ReglasNegocio.CopiasOficiales.incluirCaratula | config.json |
| ExpedicionService | procesar_oficiales | 1051 | ReglasNegocio.CopiasOficiales.Subcategorias | config.json |
| ExpedicionService | procesar_oficiales | 1051 | ReglasNegocio.CopiasOficiales.Especificaciones | config.json |
| ExpedicionService | _procesar_caso_oficial | 1101 | caso.invt_matriculasrequeridas | CRM |
| ExpedicionService | _procesar_caso_oficial | 1154 | caso.sp_ticketnumber | CRM |
| ExpedicionService | _procesar_caso_oficial | 1154 | caso.sp_name | CRM |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1321 | OneDrive.carpetaBase | config.json |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1322 | GraphAPI.user_email | config.json |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1343 | ReglasNegocio.CopiasOficiales.emailResponsable | config.json |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1347 | Globales.modo | config.json |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1351 | Globales.emailQa | config.json |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1412 | ReglasNegocio.CopiasOficiales.PlantillasEmail.default.asunto | config.json |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1412 | ReglasNegocio.CopiasOficiales.PlantillasEmail.default.cuerpo | config.json |
| ExpedicionService | _obtener_plantilla_email | 1520 | ReglasNegocio.CopiasOficiales.PlantillasEmail | config.json |
| ExpedicionService | _obtener_plantilla_email | 1528 | ReglasNegocio.Copias.Subcategorias | config.json |
| ExpedicionService | _reemplazar_variables_plantilla | 1609 | caso.sp_nombredelaempresa | CRM |
| ExpedicionService | _reemplazar_variables_plantilla | 1613 | caso.sp_name | CRM |
| ExpedicionService | _reemplazar_variables_plantilla | 1624 | caso.invt_correoelectronico | CRM |
| ExpedicionService | _reemplazar_variables_plantilla | 1629 | caso.createdon | CRM |
| ExpedicionService | _agregar_firma | 1654 | Firma.texto | config.json |
| ExpedicionService | _obtener_destinatarios_por_modo | 1695 | Globales.modo | config.json |
| ExpedicionService | _obtener_destinatarios_por_modo | 1709 | Globales.emailQa | config.json |
| ExpedicionService | _obtener_email_caso | 1725 | caso.sp_correoelectronico | CRM |
| ExpedicionService | _obtener_email_caso | 1726 | caso.emailaddress | CRM |
| ExpedicionService | _obtener_email_caso | 1727 | caso.emailaddress1 | CRM |
| ExpedicionService | _obtener_email_usuario_crm | 1775 | response.internalemailaddress | CRM (Graph API) |
| ExpedicionService | _obtener_email_usuario_crm | 1782 | response.domainname | CRM (Graph API) |
| ExpedicionService | _obtener_email_creador | 1819 | caso.invt_correoelectronico | CRM |
| ExpedicionService | _obtener_email_creador | 1825 | caso._ownerid_value | CRM |
| ExpedicionService | _obtener_email_creador | 1825 | caso._createdby_value | CRM |
| ExpedicionService | _obtener_tipo_documento | 1842 | documento.Fields[].FieldName | DocuWare |
| ExpedicionService | _generar_reporte_excel | 1887 | Reportes.CodigoAsistente | config.json |
| ExpedicionService | _generar_reporte_excel | 1899 | Reportes.UsuaroRedBR | config.json |
| ExpedicionService | _generar_reporte_excel | 1904 | Reportes.NumeroMaquinaBR | config.json |
| ExpedicionService | _generar_reporte_excel | 1943 | caso.sp_ticketnumber | CRM |
| ExpedicionService | _generar_reporte_excel | 1944 | caso.sp_name | CRM |
| ExpedicionService | _generar_reporte_excel | 1947 | caso.invt_matriculasrequeridas | CRM |
| ExpedicionService | _generar_reporte_excel | 2025 | Globales.RutaBaseProyecto | config.json |
| ExpedicionService | _enviar_reporte_por_email | 2061 | ReglasNegocio.Copias.emailResponsable | config.json |
| ExpedicionService | _enviar_reporte_por_email | 2063 | ReglasNegocio.CopiasOficiales.emailResponsable | config.json |
| ExpedicionService | _enviar_reporte_por_email | 2072 | Reportes.PlantillaEmail.asunto | config.json |
| ExpedicionService | _enviar_reporte_por_email | 2072 | Reportes.PlantillaEmail.cuerpo | config.json |
| ExpedicionService | _enviar_reporte_por_email | 2106 | GraphAPI.user_email | config.json |
| ExpedicionService | _guardar_reporte_en_bd | 2178 | Database | config.json |
| DocuWareClient | __init__ | 35 | DocuWare | config.json |
| DocuWareClient | __init__ | 39 | DocuWare.verifySSL | config.json |
| DocuWareClient | autenticar | 127 | DocuWare.tokenEndpoint | config.json |
| DocuWareClient | autenticar | 135 | DocuWare.username | config.json |
| DocuWareClient | autenticar | 136 | DocuWare.password | config.json (Rocketbot) |
| DocuWareClient | _inicializar_organization_id | 263 | DocuWare.organizationName | config.json |
| DocuWareClient | _inicializar_file_cabinet_id | 282 | DocuWare.fileCabinetName | config.json |
| DocuWareClient | _inicializar_search_dialog_id | 305 | DocuWare.searchDialogName | config.json |
| DocuWareClient | buscar_documentos | 364 | documento.Fields[].DBName | DocuWare |
| DocuWareClient | buscar_documentos | 365 | documento.Fields[].Value | DocuWare |
| DocuWareClient | _obtener_campo | 608 | documento.Fields[].FieldName | DocuWare |
| DocuWareClient | _obtener_campo | 609 | documento.Fields[].Item | DocuWare |
| DocuWareClient | _generar_nombre_archivo | 564 | documento.DWSTOREDATETIME | DocuWare |
| DocuWareClient | _generar_nombre_archivo | 572 | documento.TRDNOMBREDOCUMENTO | DocuWare |
| GraphClient | enviar_email | 186 | usuario_id | Graph API |
| GraphClient | subir_a_onedrive | 247 | usuario_id | Graph API |
| GraphClient | subir_a_onedrive | 254 | carpeta_destino | OneDrive |
| GraphClient | subir_carpeta_completa | 301 | usuario_id | Graph API |
| GraphClient | subir_carpeta_completa | 308 | carpeta_destino | OneDrive |
| GraphClient | compartir_carpeta | 489 | item_id | OneDrive |
| GraphClient | compartir_carpeta | 497 | usuario_id | Graph API |
| GraphClient | compartir_con_usuario | 554 | item_id | OneDrive |
| GraphClient | compartir_con_usuario | 562 | usuario_id | Graph API |
| GraphClient | compartir_con_usuario | 563 | email_destinatario | Email |
| GraphClient | obtener_email_enviado | 678 | usuario_id | Graph API |
| GraphClient | obtener_email_enviado | 681 | asunto | Email |
| GraphClient | obtener_email_enviado | 712 | response.value[].subject | Email (Graph API) |
| GraphClient | obtener_email_enviado | 712 | response.value[].sentDateTime | Email (Graph API) |
| GraphClient | formatear_email_legible | 810 | email_data.subject | Email (Graph API) |
| GraphClient | formatear_email_legible | 811 | email_data.sentDateTime | Email (Graph API) |
| GraphClient | formatear_email_legible | 812 | email_data.from.emailAddress | Email (Graph API) |
| GraphClient | formatear_email_legible | 813 | email_data.toRecipients | Email (Graph API) |
| GraphClient | formatear_email_legible | 814 | email_data.body | Email (Graph API) |
| GraphClient | formatear_email_legible | 849 | caso.sp_name | CRM |
| GraphClient | formatear_email_legible | 849 | caso.sp_ticketnumber | CRM |
| CRMClient | consultar_casos | 228 | filtro | CRM (OData) |
| CRMClient | obtener_caso | 308 | case_id | CRM |
| CRMClient | actualizar_caso | 321 | case_id | CRM |
| CRMClient | actualizar_caso | 327 | datos | CRM |
| NonCriticalRulesValidator | validar_reglas_no_criticas | 46 | Globales.modo | config.json |
| NonCriticalRulesValidator | validar_reglas_no_criticas | 48 | caso.invt_correoelectronico | CRM |
| NonCriticalRulesValidator | validar_reglas_no_criticas | 63 | caso.sp_name | CRM |
| NonCriticalRulesValidator | validar_reglas_no_criticas | 71 | caso.invt_matriculasrequeridas | CRM |
| ExcepcionesValidator | debe_descargar | 27 | documento.TRDNOMBREDOCUMENTO | DocuWare |
| ExcepcionesValidator | debe_descargar | 28 | documento.ACTOREGISTRADO | DocuWare |
| ExpedicionCopiasDB | __init__ | 31 | Database | config.json |
| ExpedicionCopiasDB | __init__ | 70 | Database.schema | config.json |
| ExpedicionCopiasDB | insert_reporte_expedicion | 102 | Todos los parámetros | Database |

## 3. Tabla de Strings Hardcodeados

Esta tabla identifica strings literales que deberían estar en constantes o archivos de configuración. **NO se incluyen strings que son parte de la lógica técnica** (nombres de métodos, mensajes de error técnicos, etc.).

| Clase | Método | Línea | String encontrado | Ubicación |
|-------|--------|-------|-------------------|-----------|
| ExpedicionService | _validar_franja_horaria_tipo | 112 | "Tipo desconocido: {tipo}. No se validará franja horaria." | Constantes de mensajes |
| ExpedicionService | _crear_lock | 163 | "Lock existente encontrado para {tipo}. Proceso ya en ejecución." | Constantes de mensajes |
| ExpedicionService | _crear_lock | 167 | "Lock antiguo encontrado para {tipo}. Eliminándolo." | Constantes de mensajes |
| ExpedicionService | _enviar_notificacion_error_conexion | 262 | "emailResponsable no está configurado para {tipo}. No se enviará notificación de error de conexión." | Constantes de mensajes |
| ExpedicionService | _enviar_notificacion_error_conexion | 271 | "Plantilla de notificación de error de conexión no encontrada para {tipo}. No se enviará notificación." | Constantes de mensajes |
| ExpedicionService | _enviar_notificacion_error_conexion | 278 | "Plantilla de notificación de error de conexión incompleta para {tipo}. No se enviará notificación." | Constantes de mensajes |
| ExpedicionService | _enviar_notificacion_inicio | 321 | "emailResponsable no está configurado para {tipo}. No se enviará notificación de inicio." | Constantes de mensajes |
| ExpedicionService | _enviar_notificacion_inicio | 330 | "Plantilla de notificación de inicio no encontrada para {tipo}. No se enviará notificación." | Constantes de mensajes |
| ExpedicionService | _enviar_notificacion_inicio | 337 | "Plantilla de notificación de inicio incompleta para {tipo}. No se enviará notificación." | Constantes de mensajes |
| ExpedicionService | procesar_particulares | 414 | "Interrumpido por salida de franja horaria" | Constantes de mensajes |
| ExpedicionService | procesar_particulares | 418 | "No procesado - interrupción por franja horaria" | Constantes de mensajes |
| ExpedicionService | _procesar_caso_particular | 499 | "No se encontraron documentos en DocuWare" | Constantes de mensajes |
| ExpedicionService | _procesar_caso_particular | 506 | "Todos los documentos fueron excluidos por excepciones de reglas de negocio" | Constantes de mensajes |
| ExpedicionService | _procesar_caso_particular | 511 | "Todas las descargas fallaron" | Constantes de mensajes |
| ExpedicionService | _procesar_caso_particular | 549 | "Caso procesado correctamente" | Constantes de mensajes |
| ExpedicionService | _enviar_pdf_grande | 717 | "/Particulares/" | Constantes de rutas |
| ExpedicionService | _enviar_pdf_grande | 736 | "read" | Constantes de permisos |
| ExpedicionService | _enviar_pdf_grande | 756 | "view" | Constantes de permisos |
| ExpedicionService | _enviar_email_sin_adjuntos | 863 | "emailResponsable no está configurado para {tipo}. No se enviará email." | Constantes de mensajes |
| ExpedicionService | _enviar_email_sin_adjuntos | 870 | "Plantilla sinAdjuntos no encontrada o vacía para {tipo}. No se enviará email." | Constantes de mensajes |
| ExpedicionService | _enviar_email_regla_no_critica | 920 | "emailResponsable no está configurado para {tipo}. No se enviará email." | Constantes de mensajes |
| ExpedicionService | _enviar_email_regla_no_critica | 927 | "PlantillaEmailReglasNoCriticas no está configurada para {tipo}. No se enviará email." | Constantes de mensajes |
| ExpedicionService | _enviar_email_regla_no_critica | 930 | "IMPORTANTE EXPEDICIÓN DE COPIAS - Punto de control crítico" | config.json (default) |
| ExpedicionService | _enviar_email_regla_no_critica | 934 | "Cuerpo de plantilla vacío. No se enviará email." | Constantes de mensajes |
| ExpedicionService | _enviar_email_error_compartir | 983 | "emailResponsable no está configurado para {tipo}. No se enviará email." | Constantes de mensajes |
| ExpedicionService | _enviar_email_error_compartir | 989 | "Error al compartir archivo en OneDrive - Caso {ticket_number}" | Constantes de mensajes |
| ExpedicionService | _enviar_email_error_compartir | 992 | "Estimado/a Responsable," | Constantes de plantillas |
| ExpedicionService | _enviar_email_error_compartir | 992 | "Se informa que no fue posible compartir públicamente el archivo/carpeta en OneDrive para el caso {nombre_caso} (Radicado: {ticket_number}) debido a las políticas de seguridad de la organización." | Constantes de plantillas |
| ExpedicionService | _enviar_email_error_compartir | 1002 | "El proceso continuó normalmente y se envió el enlace directo de OneDrive al destinatario. Este enlace solo es accesible para usuarios autenticados de la organización." | Constantes de plantillas |
| ExpedicionService | _enviar_email_error_compartir | 1002 | "Saludos,<br>Equipo CCMA" | Constantes de plantillas |
| ExpedicionService | procesar_oficiales | 1092 | "Interrumpido por salida de franja horaria" | Constantes de mensajes |
| ExpedicionService | procesar_oficiales | 1096 | "No procesado - interrupción por franja horaria" | Constantes de mensajes |
| ExpedicionService | _procesar_caso_oficial | 1179 | "No se encontraron documentos en DocuWare" | Constantes de mensajes |
| ExpedicionService | _procesar_caso_oficial | 1186 | "Todos los documentos fueron excluidos por excepciones de reglas de negocio" | Constantes de mensajes |
| ExpedicionService | _procesar_caso_oficial | 1191 | "Todas las descargas fallaron" | Constantes de mensajes |
| ExpedicionService | _procesar_caso_oficial | 1224 | "Caso procesado correctamente" | Constantes de mensajes |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1324 | "/Oficiales" | Constantes de rutas |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1354 | "read" | Constantes de permisos |
| ExpedicionService | _subir_y_enviar_carpeta_oficial | 1409 | "/Oficiales/" | Constantes de rutas |
| ExpedicionService | _formatear_fecha_hoy_extendida | 1546 | "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre" | Constantes de localización |
| ExpedicionService | _agregar_firma | 1658 | "Firma no configurada en config.json. No se agregará firma al correo." | Constantes de mensajes |
| ExpedicionService | _obtener_destinatarios_por_modo | 1701 | "Modo inválido '{modo}', usando PROD por defecto" | Constantes de mensajes |
| ExpedicionService | _obtener_destinatarios_por_modo | 1711 | "Modo QA configurado pero 'emailQa' no está definido en la sección Globales" | Constantes de mensajes |
| ExpedicionService | _generar_reporte_excel | 1888 | "R_CCMA_ExpedicionCopias" | config.json (default) |
| ExpedicionService | _generar_reporte_excel | 1892 | "ExpedicionCopias_Particulares" | Constantes de códigos |
| ExpedicionService | _generar_reporte_excel | 1894 | "ExpedicionCopias_Oficiales" | Constantes de códigos |
| ExpedicionService | _generar_reporte_excel | 1899 | "usuario.red" | config.json (default) |
| ExpedicionService | _generar_reporte_excel | 1904 | "MAQUINA-001" | config.json (default) |
| ExpedicionService | _generar_reporte_excel | 1917 | "Codigo Asistente" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1918 | "Codigo Bot" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1919 | "Usuario de red bot runner" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1920 | "Nombre Estacion Bot Runner" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1921 | "ID Proceso" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1922 | "No Radicado" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1923 | "Matricuas" | Constantes de headers (typo) |
| ExpedicionService | _generar_reporte_excel | 1924 | "Estado proceso" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1925 | "Observación" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1926 | "Fecha Inicio de ejecución" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1927 | "Hora Inicio de ejecución" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1928 | "Fecha Fin de ejecución" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1929 | "Hora Fin de ejecución" | Constantes de headers |
| ExpedicionService | _generar_reporte_excel | 1959 | "Exitoso" | Constantes de estados |
| ExpedicionService | _generar_reporte_excel | 1960 | "Procesado correctamente" | Constantes de mensajes |
| ExpedicionService | _generar_reporte_excel | 1987 | "No Exitoso" | Constantes de estados |
| ExpedicionService | _generar_reporte_excel | 2005 | "Pendiente" | Constantes de estados |
| ExpedicionService | _generar_reporte_excel | 2005 | "No procesado" | Constantes de mensajes |
| ExpedicionService | _generar_reporte_excel | 2026 | "reportes" | Constantes de rutas |
| ExpedicionService | _generar_reporte_excel | 2030 | "reporte_expedicion_{timestamp}.xlsx" | Constantes de nombres de archivo |
| ExpedicionService | _enviar_reporte_por_email | 2068 | "emailResponsable no está configurado para {tipo}. No se enviará reporte por email." | Constantes de mensajes |
| ExpedicionService | _enviar_reporte_por_email | 2076 | "PlantillaEmail no está configurada en Reportes. No se enviará reporte por email." | Constantes de mensajes |
| ExpedicionService | _enviar_reporte_por_email | 2079 | "Reporte de Ejecución - Expedición de Copias" | config.json (default) |
| ExpedicionService | _enviar_reporte_por_email | 2080 | "<html><body><p>Estimado/a Responsable,</p><p>Se adjunta el reporte de ejecución.</p><p>Saludos,<br>Equipo CCMA</p></body></html>" | config.json (default) |
| ExpedicionService | _enviar_reporte_por_email | 2083 | "PARTICULARES" | Constantes de tipos |
| ExpedicionService | _enviar_reporte_por_email | 2083 | "OFICIALES" | Constantes de tipos |
| ExpedicionService | _enviar_email_error_caso | 1851 | "Error en procesamiento de caso {sp_ticketnumber}" | Constantes de mensajes |
| ExpedicionService | _enviar_email_error_caso | 1852 | "<html><body><p>Estimado/a,</p><p>Se presentó un error al procesar su caso:</p><p>{mensaje}</p><p>Por favor contacte al administrador.</p></body></html>" | Constantes de plantillas |
| ExpedicionService | _guardar_reporte_en_bd | 2180 | "Configuración de Database no encontrada. No se guardará reporte en BD." | Constantes de mensajes |
| ExpedicionService | _guardar_reporte_en_bd | 2185 | "Password de Database no configurado (debe obtenerse desde rocketbot). No se guardará reporte en BD." | Constantes de mensajes |
| ExpedicionService | _guardar_reporte_en_bd | 2212 | "Exitoso" | Constantes de estados |
| ExpedicionService | _guardar_reporte_en_bd | 2213 | "Procesado correctamente" | Constantes de mensajes |
| ExpedicionService | _guardar_reporte_en_bd | 2242 | "No Exitoso" | Constantes de estados |
| ExpedicionService | _guardar_reporte_en_bd | 2272 | "Pendiente" | Constantes de estados |
| ExpedicionService | _guardar_reporte_en_bd | 2262 | "No procesado" | Constantes de mensajes |
| DocuWareClient | autenticar | 139 | "Username de DocuWare no está configurado en la sección DocuWare" | Constantes de mensajes |
| DocuWareClient | autenticar | 141 | "Password de DocuWare no está configurado. Verifica que la variable de Rocketbot 'docuware_password' esté configurada" | Constantes de mensajes |
| DocuWareClient | autenticar | 147 | "docuware.platform" | Constantes de scopes |
| DocuWareClient | autenticar | 148 | "docuware.platform.net.client" | Constantes de client_id |
| DocuWareClient | buscar_documentos | 364 | "MATRICULA" | Constantes de campos DocuWare |
| DocuWareClient | buscar_documentos | 371 | "DWSTOREDATETIME" | Constantes de campos DocuWare |
| DocuWareClient | buscar_documentos | 372 | "Asc" | Constantes de ordenamiento |
| DocuWareClient | _generar_nombre_archivo | 570 | "NODATE" | Constantes de valores por defecto |
| DocuWareClient | _generar_nombre_archivo | 574 | "NODOCNAME" | Constantes de valores por defecto |
| DocuWareClient | _generar_nombre_archivo | 576 | ".pdf" | Constantes de extensiones |
| DocuWareClient | _generar_nombre_archivo | 578 | ".tiff" | Constantes de extensiones |
| DocuWareClient | _generar_nombre_archivo | 580 | ".jpg" | Constantes de extensiones |
| DocuWareClient | _generar_nombre_archivo | 582 | ".png" | Constantes de extensiones |
| DocuWareClient | _es_sobre | 625 | "PyMuPDF no está instalado. No se pueden detectar archivos embebidos." | Constantes de mensajes |
| DocuWareClient | _extraer_y_mergear_adjuntos_sobre | 656 | "PyMuPDF no está instalado. Instala con: pip install PyMuPDF" | Constantes de mensajes |
| DocuWareClient | _extraer_y_mergear_adjuntos_sobre | 668 | "El PDF no tiene archivos embebidos" | Constantes de mensajes |
| DocuWareClient | _extraer_y_mergear_adjuntos_sobre | 715 | "No se pudo extraer ningún PDF válido de los attachments" | Constantes de mensajes |
| GraphClient | enviar_email | 210 | "HTML" | Constantes de tipos de contenido |
| GraphClient | enviar_email | 210 | "Text" | Constantes de tipos de contenido |
| GraphClient | enviar_email | 230 | "#microsoft.graph.fileAttachment" | Constantes de tipos OData |
| GraphClient | enviar_email | 232 | "application/pdf" | Constantes de tipos MIME |
| GraphClient | enviar_email | 241 | "true" | Constantes de valores booleanos |
| GraphClient | compartir_carpeta | 511 | "view" | Constantes de tipos de enlace |
| GraphClient | compartir_carpeta | 511 | "edit" | Constantes de tipos de enlace |
| GraphClient | compartir_carpeta | 512 | "anonymous" | Constantes de scopes |
| GraphClient | compartir_carpeta | 538 | "organization" | Constantes de scopes |
| GraphClient | compartir_con_usuario | 576 | "write" | Constantes de roles |
| GraphClient | compartir_con_usuario | 579 | "read" | Constantes de roles |
| GraphClient | compartir_con_usuario | 589 | "Se ha compartido un archivo con usted. Puede acceder a través del enlace en este correo." | Constantes de mensajes |
| GraphClient | _formatear_fecha_hora_email | 920 | "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre" | Constantes de localización |
| CRMClient | _get_token | 69 | "/api/" | Constantes de rutas |
| CRMClient | _get_token | 70 | "/.default" | Constantes de scopes |
| CRMClient | _procesar_error_403 | 215 | "⚠️  La aplicación no tiene acceso al ambiente de Dynamics 365." | Constantes de mensajes |
| CRMClient | consultar_casos | 243 | "5000" | Constantes de límites |
| CRMClient | consultar_casos | 244 | "createdon desc" | Constantes de ordenamiento |
| NonCriticalRulesValidator | validar_reglas_no_criticas | 52 | "El campo invt_correoelectronico está vacío. Este es el email de respuesta final cuando mode=PROD." | Constantes de mensajes |
| NonCriticalRulesValidator | validar_reglas_no_criticas | 58 | "El email invt_correoelectronico '{email}' no tiene un formato válido. Este es el email de respuesta final cuando mode=PROD." | Constantes de mensajes |
| NonCriticalRulesValidator | validar_reglas_no_criticas | 67 | "No se logró extraer el número de radicado (sp_name) del PQRS en el CRM." | Constantes de mensajes |
| NonCriticalRulesValidator | validar_reglas_no_criticas | 75 | "No se logró extraer la(s) matrícula(s) (invt_matriculasrequeridas) del PQRS en el CRM." | Constantes de mensajes |
| NonCriticalRulesValidator | validar_reglas_no_criticas | 83 | "No se encontraron matrículas válidas en invt_matriculasrequeridas después de procesar el campo." | Constantes de mensajes |
| ExpedicionCopiasDB | __init__ | 70 | "ExpedicionCopiasDbo" | config.json (default) |
| ExpedicionCopiasDB | insert_reporte_expedicion | 143 | "INSERT INTO {table_name} (...)" | Constantes de SQL (debería estar en queries separadas) |

## 4. Recomendaciones Generales

### 4.1. Prioridad Alta

1. **Estandarizar uso de campos de email**:
   - Crear método único `_obtener_email_destinatario()` que use siempre `invt_correoelectronico`
   - Documentar claramente la diferencia entre campos de email
   - Actualizar todos los lugares donde se obtiene email para usar el método estandarizado

2. **Corregir typo en configuración**:
   - Cambiar `UsuaroRedBR` → `UsuarioRedBR` en `config.example.json` y código

3. **Estandarizar nombres de variables en plantillas**:
   - Crear archivo de constantes con nombres de variables permitidas
   - Validar que todas las variantes se reemplacen correctamente

### 4.2. Prioridad Media

1. **Crear archivo de constantes**:
   - Mover todos los strings hardcodeados identificados a un archivo `constants.py`
   - Organizar por categorías: mensajes, rutas, estados, tipos, etc.

2. **Estandarizar convención de nombres de configuración**:
   - Usar camelCase para todas las claves
   - Documentar la convención en `config.example.json`

3. **Documentar uso de campos de radicado**:
   - Crear documentación clara sobre cuándo usar `sp_name` vs `sp_ticketnumber`
   - Estandarizar la lógica de combinación en reportes

### 4.3. Prioridad Baja

1. **Mejorar manejo de errores**:
   - Centralizar mensajes de error en constantes
   - Hacer mensajes más descriptivos y consistentes

2. **Optimizar consultas a CRM**:
   - Revisar si todos los campos en `ALL_FIELDS` son necesarios
   - Considerar paginación más eficiente

3. **Mejorar logging**:
   - Estandarizar formato de mensajes de log
   - Agregar más contexto en mensajes de error

## 5. Conclusión

El módulo ExpedicionCopias está bien estructurado, pero presenta algunas inconsistencias que pueden mejorarse. Las principales áreas de mejora son:

- **Estandarización de campos**: Especialmente en el uso de campos de email y radicado
- **Centralización de strings**: Muchos strings deberían estar en constantes o configuración
- **Documentación**: Mejorar documentación sobre el uso de campos y convenciones

**Total de inconsistencias identificadas**: 5  
**Total de variables externas mapeadas**: 150+  
**Total de strings hardcodeados identificados**: 100+

Se recomienda abordar las inconsistencias de prioridad alta primero, ya que tienen mayor impacto en la funcionalidad y mantenibilidad del módulo.
