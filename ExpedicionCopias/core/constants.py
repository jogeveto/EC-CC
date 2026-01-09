"""Constantes centralizadas para el módulo ExpedicionCopias."""

# ============================================================================
# CAMPOS CRM
# ============================================================================

# Campo principal para número de radicado
CAMPO_RADICADO_PRINCIPAL = "sp_name"

# Campo alternativo de ticket (solo para consultas, no para lógica de negocio)
CAMPO_TICKET_ALTERNATIVO = "sp_ticketnumber"

# Campos de email para particulares
CAMPO_EMAIL_PARTICULARES = "sp_correoelectronico"

# Campos de email para oficiales (se usa emailResponsable de config)
CAMPO_EMAIL_OFICIALES_CONFIG = "emailResponsable"

# Campo de email del creador/destinatario del caso
CAMPO_EMAIL_CREADOR = "invt_correoelectronico"

# Otros campos CRM
CAMPO_NOMBRE_SOCIEDAD = "sp_nombredelaempresa"
CAMPO_MATRICULAS = "invt_matriculasrequeridas"
CAMPO_SUBCATEGORIA = "_sp_subcategoriapqrs_value"
CAMPO_FECHA_CREACION = "createdon"
CAMPO_OWNER_ID = "_ownerid_value"
CAMPO_CREATED_BY = "_createdby_value"

# ============================================================================
# VARIABLES DE PLANTILLAS
# ============================================================================

# Variables estándar de plantillas (todas las variantes)
VARIABLE_NOMBRE_SOCIEDAD = "[Nombre de la sociedad]"
VARIABLE_NUMERO_PQRS = "[Número PQRS]"
VARIABLE_FECHA_HOY = "[Fecha hoy]"
VARIABLE_CLIENTE = "[CLIENTE]"
VARIABLE_CORREO_ELECTRONICO = "[Correo electrónico]"
VARIABLE_CORREO_ELECTRONICO_VARIANTE = "[Correo Electrónico]"  # Variante con mayúscula
VARIABLE_FECHA_INGRESO = "[Fecha de ingreso de la solicitud]"
VARIABLE_ENLACE_ONEDRIVE = "[Enlace Onedrive.pdf]"
VARIABLE_ENLACE_ONEDRIVE_VARIANTE = "[​Enlace Onedrive.pdf​]"  # Variante con caracteres especiales
VARIABLE_FECHA_RESPUESTA = "[Fecha de respuesta]"

# Lista de todas las variantes de variables de plantilla para reemplazo
VARIANTES_VARIABLES_PLANTILLA = [
    (VARIABLE_CORREO_ELECTRONICO, VARIABLE_CORREO_ELECTRONICO_VARIANTE),
    (VARIABLE_ENLACE_ONEDRIVE, VARIABLE_ENLACE_ONEDRIVE_VARIANTE),
]

# ============================================================================
# RUTAS
# ============================================================================

RUTA_PARTICULARES = "/Particulares/"
RUTA_OFICIALES = "/Oficiales"
RUTA_OFICIALES_SLASH = "/Oficiales/"
RUTA_REPORTES = "reportes"
RUTA_API = "/api/"
RUTA_DEFAULT_SCOPE = "/.default"

# ============================================================================
# PERMISOS Y ROLES
# ============================================================================

PERMISO_READ = "read"
PERMISO_VIEW = "view"
PERMISO_WRITE = "write"
ROL_READ = "read"
ROL_WRITE = "write"

# ============================================================================
# ESTADOS DE PROCESO
# ============================================================================

ESTADO_EXITOSO = "Exitoso"
ESTADO_NO_EXITOSO = "No Exitoso"
ESTADO_PENDIENTE = "Pendiente"
MENSAJE_PROCESADO_CORRECTAMENTE = "Procesado correctamente"
MENSAJE_NO_PROCESADO = "No procesado"

# ============================================================================
# TIPOS DE CONTENIDO
# ============================================================================

TIPO_CONTENIDO_HTML = "HTML"
TIPO_CONTENIDO_TEXT = "Text"
TIPO_MIME_PDF = "application/pdf"
TIPO_ODATA_ATTACHMENT = "#microsoft.graph.fileAttachment"

# ============================================================================
# TIPOS DE ENLACE Y SCOPE
# ============================================================================

TIPO_ENLACE_VIEW = "view"
TIPO_ENLACE_EDIT = "edit"
SCOPE_ANONYMOUS = "anonymous"
SCOPE_ORGANIZATION = "organization"

# ============================================================================
# CAMPOS DOCUWARE
# ============================================================================

CAMPO_DOCUWARE_MATRICULA = "MATRICULA"
CAMPO_DOCUWARE_DWSTOREDATETIME = "DWSTOREDATETIME"
CAMPO_DOCUWARE_TRDNOMBREDOCUMENTO = "TRDNOMBREDOCUMENTO"
CAMPO_DOCUWARE_ACTOREGISTRADO = "ACTOREGISTRADO"
ORDEN_ASC = "Asc"

# ============================================================================
# VALORES POR DEFECTO
# ============================================================================

VALOR_DEFECTO_NODATE = "NODATE"
VALOR_DEFECTO_NODOCNAME = "NODOCNAME"
VALOR_DEFECTO_NA = "N/A"
VALOR_DEFECTO_TRUE = "true"
VALOR_DEFECTO_CODIGO_ASISTENTE = "R_CCMA_ExpedicionCopias"
VALOR_DEFECTO_USUARIO_RED = "usuario.red"
VALOR_DEFECTO_MAQUINA = "MAQUINA-001"
VALOR_DEFECTO_ESQUEMA = "ExpedicionCopiasDbo"

# ============================================================================
# EXTENSIONES DE ARCHIVO
# ============================================================================

EXTENSION_PDF = ".pdf"
EXTENSION_TIFF = ".tiff"
EXTENSION_JPG = ".jpg"
EXTENSION_PNG = ".png"
EXTENSION_XLSX = ".xlsx"

# ============================================================================
# CÓDIGOS DE BOT
# ============================================================================

CODIGO_BOT_PARTICULARES = "ExpedicionCopias_Particulares"
CODIGO_BOT_OFICIALES = "ExpedicionCopias_Oficiales"

# ============================================================================
# HEADERS DE REPORTES EXCEL
# ============================================================================

HEADER_CODIGO_ASISTENTE = "Codigo Asistente"
HEADER_CODIGO_BOT = "Codigo Bot"
HEADER_USUARIO_RED = "Usuario de red bot runner"
HEADER_NOMBRE_ESTACION = "Nombre Estacion Bot Runner"
HEADER_ID_PROCESO = "ID Proceso"
HEADER_NO_RADICADO = "No Radicado"
HEADER_MATRICULAS = "Matricuas"  # Nota: typo original mantenido por compatibilidad
HEADER_ESTADO_PROCESO = "Estado proceso"
HEADER_OBSERVACION = "Observación"
HEADER_FECHA_INICIO = "Fecha Inicio de ejecución"
HEADER_HORA_INICIO = "Hora Inicio de ejecución"
HEADER_FECHA_FIN = "Fecha Fin de ejecución"
HEADER_HORA_FIN = "Hora Fin de ejecución"

# ============================================================================
# TIPOS DE PROCESO
# ============================================================================

TIPO_PARTICULARES = "PARTICULARES"
TIPO_OFICIALES = "OFICIALES"
TIPO_COPIAS = "Copias"
TIPO_COPIAS_OFICIALES = "CopiasOficiales"

# ============================================================================
# LÍMITES Y CONFIGURACIÓN
# ============================================================================

LIMITE_CONSULTA_CRM = "5000"
ORDENAMIENTO_CRM = "createdon desc"

# ============================================================================
# SCOPES Y CLIENT IDS
# ============================================================================

SCOPE_DOCUWARE_PLATFORM = "docuware.platform"
CLIENT_ID_DOCUWARE = "docuware.platform.net.client"

# ============================================================================
# MESES EN ESPAÑOL (LOCALIZACIÓN)
# ============================================================================

MESES_ESPAÑOL = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

# ============================================================================
# MENSAJES DE ERROR Y LOG
# ============================================================================

# Mensajes de validación
MSG_TIPO_DESCONOCIDO = "Tipo desconocido: {tipo}. No se validará franja horaria."
MSG_LOCK_EXISTENTE = "Lock existente encontrado para {tipo}. Proceso ya en ejecución."
MSG_LOCK_ANTIGUO = "Lock antiguo encontrado para {tipo}. Eliminándolo."

# Mensajes de configuración
MSG_EMAIL_RESPONSABLE_NO_CONFIG = "emailResponsable no está configurado para {tipo}. No se enviará {accion}."
MSG_PLANTILLA_NO_ENCONTRADA = "Plantilla de {tipo_plantilla} no encontrada para {tipo}. No se enviará {accion}."
MSG_PLANTILLA_INCOMPLETA = "Plantilla de {tipo_plantilla} incompleta para {tipo}. No se enviará {accion}."
MSG_PLANTILLA_SIN_ADJUNTOS_NO_ENCONTRADA = "Plantilla sinAdjuntos no encontrada o vacía para {tipo}. No se enviará email."
MSG_PLANTILLA_REGLAS_NO_CRITICAS_NO_CONFIG = "PlantillaEmailReglasNoCriticas no está configurada para {tipo}. No se enviará email."
MSG_CUERPO_PLANTILLA_VACIO = "Cuerpo de plantilla vacío. No se enviará email."
MSG_FIRMA_NO_CONFIG = "Firma no configurada en config.json. No se agregará firma al correo."
MSG_MODO_INVALIDO = "Modo inválido '{modo}', usando PROD por defecto"
MSG_EMAIL_QA_NO_CONFIG = "Modo QA configurado pero 'emailQa' no está definido en la sección Globales"
MSG_PLANTILLA_EMAIL_NO_CONFIG = "PlantillaEmail no está configurada en Reportes. No se enviará reporte por email."
MSG_DATABASE_NO_CONFIG = "Configuración de Database no encontrada. No se guardará reporte en BD."
MSG_DATABASE_PASSWORD_NO_CONFIG = "Password de Database no configurado (debe obtenerse desde rocketbot). No se guardará reporte en BD."

# Mensajes de proceso
MSG_INTERRUMPIDO_FRANJA = "Interrumpido por salida de franja horaria"
MSG_NO_PROCESADO_FRANJA = "No procesado - interrupción por franja horaria"
MSG_NO_DOCUMENTOS = "No se encontraron documentos en DocuWare"
MSG_TODOS_EXCLUIDOS = "Todos los documentos fueron excluidos por excepciones de reglas de negocio"
MSG_TODAS_DESCARGAS_FALLARON = "Todas las descargas fallaron"
MSG_CASO_PROCESADO = "Caso procesado correctamente"

# Mensajes de error
MSG_ERROR_COMPARTIR = "Error al compartir archivo en OneDrive - Caso {ticket_number}"
MSG_ERROR_PROCESAMIENTO = "Error en procesamiento de caso {sp_ticketnumber}"

# Mensajes de DocuWare
MSG_DOCUWARE_USERNAME_NO_CONFIG = "Username de DocuWare no está configurado en la sección DocuWare"
MSG_DOCUWARE_PASSWORD_NO_CONFIG = "Password de DocuWare no está configurado. Verifica que la variable de Rocketbot 'docuware_password' esté configurada"
MSG_PYMUPDF_NO_INSTALADO = "PyMuPDF no está instalado. No se pueden detectar archivos embebidos."
MSG_PYMUPDF_INSTALAR = "PyMuPDF no está instalado. Instala con: pip install PyMuPDF"
MSG_PDF_SIN_EMBEBIDOS = "El PDF no tiene archivos embebidos"
MSG_NO_PDF_VALIDO = "No se pudo extraer ningún PDF válido de los attachments"

# Mensajes de CRM
MSG_CRM_SIN_ACCESO = "⚠️  La aplicación no tiene acceso al ambiente de Dynamics 365."

# Mensajes de validación de reglas no críticas
MSG_EMAIL_VACIO = "El campo invt_correoelectronico está vacío. Este es el email de respuesta final cuando mode=PROD."
MSG_EMAIL_INVALIDO = "El email invt_correoelectronico '{email}' no tiene un formato válido. Este es el email de respuesta final cuando mode=PROD."
MSG_RADICADO_NO_EXTRAIDO = "No se logró extraer el número de radicado (sp_name) del PQRS en el CRM."
MSG_MATRICULAS_NO_EXTRAIDAS = "No se logró extraer la(s) matrícula(s) (invt_matriculasrequeridas) del PQRS en el CRM."
MSG_MATRICULAS_NO_VALIDAS = "No se encontraron matrículas válidas en invt_matriculasrequeridas después de procesar el campo."

# ============================================================================
# PLANTILLAS DE EMAIL HARDCODEADAS
# ============================================================================

PLANTILLA_ERROR_COMPARTIR_ASUNTO = "Error al compartir archivo en OneDrive - Caso {ticket_number}"
PLANTILLA_ERROR_COMPARTIR_SALUDO = "Estimado/a Responsable,"
PLANTILLA_ERROR_COMPARTIR_CUERPO = (
    "Se informa que no fue posible compartir públicamente el archivo/carpeta en OneDrive "
    "para el caso {nombre_caso} (Radicado: {ticket_number}) debido a las políticas de seguridad de la organización."
)
PLANTILLA_ERROR_COMPARTIR_CONTINUACION = (
    "El proceso continuó normalmente y se envió el enlace directo de OneDrive al destinatario. "
    "Este enlace solo es accesible para usuarios autenticados de la organización."
)
PLANTILLA_ERROR_COMPARTIR_FIRMA = "Saludos,<br>Equipo CCMA"

PLANTILLA_ERROR_CASO_ASUNTO = "Error en procesamiento de caso {sp_ticketnumber}"
PLANTILLA_ERROR_CASO_CUERPO = (
    "<html><body><p>Estimado/a,</p><p>Se presentó un error al procesar su caso:</p>"
    "<p>{mensaje}</p><p>Por favor contacte al administrador.</p></body></html>"
)

PLANTILLA_REPORTE_ASUNTO = "Reporte de Ejecución - Expedición de Copias"
PLANTILLA_REPORTE_CUERPO = (
    "<html><body><p>Estimado/a Responsable,</p><p>Se adjunta el reporte de ejecución.</p>"
    "<p>Saludos,<br>Equipo CCMA</p></body></html>"
)

PLANTILLA_REGLAS_NO_CRITICAS_ASUNTO = "IMPORTANTE EXPEDICIÓN DE COPIAS - Punto de control crítico"

# ============================================================================
# MENSAJES DE COMPARTIR
# ============================================================================

MSG_COMPARTIR_ARCHIVO = "Se ha compartido un archivo con usted. Puede acceder a través del enlace en este correo."

# ============================================================================
# FORMATOS DE ARCHIVO
# ============================================================================

FORMATO_NOMBRE_REPORTE = "reporte_expedicion_{timestamp}.xlsx"
