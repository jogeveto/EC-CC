# Guía de Implementación: ExpedicionCopias en Rocketbot

Esta guía te llevará paso a paso para implementar el módulo **ExpedicionCopias** en Rocketbot.

---

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Preparación del Entorno](#preparación-del-entorno)
3. [Configuración de Variables de Rocketbot](#configuración-de-variables-de-rocketbot)
4. [Creación del Archivo de Configuración JSON](#creación-del-archivo-de-configuración-json)
5. [Despliegue del Módulo](#despliegue-del-módulo)
6. [Instalación de Dependencias](#instalación-de-dependencias)
7. [Configuración en Rocketbot](#configuración-en-rocketbot)
8. [Pruebas Iniciales](#pruebas-iniciales)
9. [Creación de Workflows](#creación-de-workflows)
10. [Solución de Problemas](#solución-de-problemas)

---

## 1. Requisitos Previos

### Software Necesario

- ✅ **Rocketbot** instalado y funcionando
- ✅ **Python 3.8+** (si necesitas ejecutar scripts manualmente)
- ✅ Acceso a **Dynamics 365 CRM**
- ✅ Acceso a **DocuWare**
- ✅ Acceso a **Microsoft Graph API** (Azure AD)
- ✅ **OneDrive** (para almacenar documentos grandes)
- ✅ (Opcional) **Base de Datos SQL Server** para auditoría

### Credenciales Requeridas

Necesitarás tener a mano:

- **Dynamics 365 CRM:**
  - Tenant ID
  - Client ID
  - Client Secret
  - URL base del CRM

- **Microsoft Graph API:**
  - Tenant ID (puede ser el mismo que Dynamics)
  - Client ID
  - Client Secret
  - Email del usuario que enviará los correos

- **DocuWare:**
  - URL del servidor
  - Username
  - Password

- **OneDrive:**
  - Carpeta base donde se almacenarán los documentos

---

## 2. Preparación del Entorno

### 2.1. Verificar Estructura del Proyecto

Asegúrate de tener la siguiente estructura:

```
Expedicion-copias/
├── ExpedicionCopias/
│   ├── __init__.py
│   ├── package.json
│   ├── requirements.txt
│   ├── core/
│   └── services/
├── shared/
│   ├── core/
│   ├── database/
│   └── utils/
└── deploy_to_rocketbot.py
```

### 2.2. Ruta de Instalación de Rocketbot

Identifica la ruta de instalación de Rocketbot. Generalmente está en:

- **Windows**: `C:\Program Files\Rocketbot\` o `C:\Users\[usuario]\Downloads\rocketbot_win_[fecha]\Rocketbot\`
- **Linux**: `/opt/rocketbot/` o `/home/[usuario]/rocketbot/`

La carpeta de módulos debe estar en: `[Rocketbot]/modules/`

---

## 3. Configuración de Variables de Rocketbot

El módulo **ExpedicionCopias** requiere las siguientes variables de Rocketbot para almacenar credenciales de forma segura.

### 3.1. Crear Variables en Rocketbot

1. Abre **Rocketbot**
2. Ve a **Configuración** → **Variables Globales** (o **Variables de Proceso**)
3. Crea las siguientes variables:

| Nombre de Variable | Descripción | Ejemplo |
|-------------------|-------------|---------|
| `graph_client_secret` | Client Secret de Microsoft Graph API | `abc123...xyz` |
| `dynamics_client_secret` | Client Secret de Dynamics 365 CRM | `def456...uvw` |
| `docuware_password` | Contraseña de DocuWare | `MiPassword123!` |
| `database_password` | Contraseña de base de datos (opcional) | `DbPass456!` |

**⚠️ Importante:** 
- Estas variables contienen información sensible
- No las incluyas en el archivo de configuración JSON
- El módulo las lee automáticamente desde Rocketbot

---

## 4. Creación del Archivo de Configuración JSON

Crea un archivo JSON con la configuración completa del módulo. Puedes guardarlo en cualquier ubicación accesible desde Rocketbot.

### 4.1. Estructura del Archivo de Configuración

Crea un archivo llamado `config_expedicion_copias.json` con el siguiente contenido:

```json
{
  "Dynamics365": {
    "tenant_id": "TU_TENANT_ID",
    "client_id": "TU_CLIENT_ID",
    "base_url": "https://tu-org.crm.dynamics.com"
  },
  "GraphAPI": {
    "tenant_id": "TU_TENANT_ID",
    "client_id": "TU_CLIENT_ID",
    "user_email": "usuario@tudominio.com"
  },
  "DocuWare": {
    "url": "https://tu-servidor.docuware.cloud/DocuWare/Platform",
    "username": "tu_usuario_docuware",
    "file_cabinet_id": "TU_FILE_CABINET_ID",
    "dialogs": [
      {
        "dialog_id": "TU_DIALOG_ID",
        "nombre": "BusquedaDocumentos"
      }
    ]
  },
  "OneDrive": {
    "carpetaBase": "/ExpedicionCopias"
  },
  "ReglasNegocio": {
    "Copias": {
      "Subcategorias": [
        "SUBCAT_ID_1",
        "SUBCAT_ID_2"
      ],
      "Especificaciones": [
        "ESPEC_ID_1",
        "ESPEC_ID_2"
      ],
      "FranjasHorarias": [
        {
          "dia": "Lunes",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        },
        {
          "dia": "Martes",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        },
        {
          "dia": "Miercoles",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        },
        {
          "dia": "Jueves",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        },
        {
          "dia": "Viernes",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        }
      ],
      "ExcepcionesDescarga": [
        {
          "tipo": "TipoDocumento",
          "valor": "TipoExcluido",
          "accion": "excluir"
        }
      ],
      "PlantillasEmail": {
        "SUBCAT_ID_1": {
          "adjunto": {
            "asunto": "Expedición de Copias - Documentos Adjuntos",
            "cuerpo": "<html><body><p>Estimado/a,</p><p>Adjunto encontrará los documentos solicitados.</p><p>Saludos cordiales.</p></body></html>"
          },
          "onedrive": {
            "asunto": "Expedición de Copias - Enlace de Descarga",
            "cuerpo": "<html><body><p>Estimado/a,</p><p>Debido al tamaño de los documentos, los encontrará disponibles en el siguiente enlace:</p><p><a href=\"{link}\">{link}</a></p><p>Saludos cordiales.</p></body></html>"
          }
        }
      }
    },
    "CopiasOficiales": {
      "Subcategorias": [
        "SUBCAT_OFICIAL_ID_1"
      ],
      "Especificaciones": [
        "ESPEC_OFICIAL_ID_1"
      ],
      "FranjasHorarias": [
        {
          "dia": "Lunes",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        },
        {
          "dia": "Martes",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        },
        {
          "dia": "Miercoles",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        },
        {
          "dia": "Jueves",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        },
        {
          "dia": "Viernes",
          "horaInicio": "08:00",
          "horaFin": "17:00"
        }
      ],
      "ExcepcionesDescarga": [],
      "PlantillasEmail": {
        "default": {
          "asunto": "Expedición de Copias Oficiales",
          "cuerpo": "<html><body><p>Estimado/a,</p><p>Los documentos solicitados están disponibles en el siguiente enlace:</p><p><a href=\"{link}\">{link}</a></p><p>Saludos cordiales.</p></body></html>"
        }
      }
    }
  },
  "Globales": {
    "RutaBaseProyecto": "C:\\Rocketbot\\ExpedicionCopias"
  },
  "Logs": {
    "RutaLogAuditoria": "C:\\Rocketbot\\Logs",
    "NombreLogAuditoria": "expedicion_copias.log"
  }
}
```

### 4.2. Explicación de las Secciones

#### Dynamics365
- `tenant_id`: ID del tenant de Azure AD
- `client_id`: ID de la aplicación registrada en Azure AD
- `base_url`: URL base de tu instancia de Dynamics 365 CRM

#### GraphAPI
- `tenant_id`: ID del tenant de Azure AD (puede ser el mismo que Dynamics)
- `client_id`: ID de la aplicación registrada en Azure AD
- `user_email`: Email del usuario que enviará los correos

#### DocuWare
- `url`: URL completa del servidor DocuWare
- `username`: Nombre de usuario de DocuWare
- `file_cabinet_id`: ID del file cabinet en DocuWare
- `dialogs`: Lista de diálogos de búsqueda disponibles

#### OneDrive
- `carpetaBase`: Carpeta base donde se almacenarán los documentos grandes

#### ReglasNegocio

**Copias** (Para particulares):
- `Subcategorias`: Lista de IDs de subcategorías a procesar
- `Especificaciones`: Lista de IDs de especificaciones a procesar
- `FranjasHorarias`: Días y horas en que el proceso puede ejecutarse
- `ExcepcionesDescarga`: Reglas para excluir ciertos tipos de documentos
- `PlantillasEmail`: Plantillas HTML para los emails según subcategoría

**CopiasOficiales** (Para entidades oficiales):
- Similar estructura a Copias
- `PlantillasEmail`: Usa una plantilla `default` única

#### Globales
- `RutaBaseProyecto`: Ruta base donde se guardarán reportes y archivos temporales

#### Logs
- `RutaLogAuditoria`: Carpeta donde se guardarán los logs
- `NombreLogAuditoria`: Nombre del archivo de log

### 4.3. Obtener IDs de Dynamics 365

Para obtener los IDs de subcategorías y especificaciones:

1. Conéctate a Dynamics 365
2. Ve a **Configuración** → **Personalización**
3. Busca las entidades de subcategorías y especificaciones
4. Obtén los GUIDs correspondientes

---

## 5. Despliegue del Módulo

### 5.1. Configurar el Script de Despliegue

Edita el archivo `deploy_to_rocketbot.py` y actualiza la ruta de Rocketbot:

```python
ROCKETBOT_MODULES_PATH = r"C:\Ruta\A\Rocketbot\modules"
```

### 5.2. Ejecutar el Despliegue

1. Abre una terminal en la carpeta raíz del proyecto
2. Ejecuta:

```bash
python deploy_to_rocketbot.py
```

El script:
- ✅ Cerrará Rocketbot si está ejecutándose
- ✅ Copiará el módulo `ExpedicionCopias` a la carpeta de módulos
- ✅ Copiará la carpeta `shared` (si no existe ya)
- ✅ Opcionalmente, abrirá Rocketbot automáticamente

### 5.3. Verificar el Despliegue

Verifica que los archivos se copiaron correctamente:

```
[Rocketbot]/modules/
├── ExpedicionCopias/
│   ├── __init__.py
│   ├── package.json
│   ├── core/
│   └── services/
└── shared/
    ├── core/
    ├── database/
    └── utils/
```

---

## 6. Instalación de Dependencias

### 6.1. Dependencias del Módulo

El módulo requiere las siguientes dependencias (ver `requirements.txt`):

```
pypdf>=3.0.0
msal>=1.24.0
holidays>=0.34
openpyxl>=3.1.0
requests>=2.31.0
azure-identity>=1.15.0
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
```

### 6.2. Instalar Dependencias

**Opción A: Usando pip (recomendado para desarrollo)**

```bash
cd ExpedicionCopias
pip install -r requirements.txt
```

**Opción B: Instalar en el entorno de Rocketbot**

Si Rocketbot tiene su propio entorno Python:

```bash
# Ubicar el Python de Rocketbot
# Generalmente en: [Rocketbot]/python/python.exe

[Rocketbot]/python/python.exe -m pip install -r requirements.txt
```

**Nota:** Rocketbot suele manejar las dependencias automáticamente, pero si hay errores de importación, instálalas manualmente.

---

## 7. Configuración en Rocketbot

### 7.1. Reiniciar Rocketbot

1. Cierra Rocketbot completamente
2. Ábrelo de nuevo para que cargue el nuevo módulo

### 7.2. Verificar que el Módulo se Cargó

1. En Rocketbot, ve a la sección de **Módulos** o **Scripts**
2. Busca **"Expedición de Copias"** o **"ExpedicionCopias"**
3. Deberías ver 3 acciones disponibles:
   - **Procesar Copias**
   - **Procesar Copias Oficiales**
   - **Verificar Conexión**

---

## 8. Pruebas Iniciales

### 8.1. Prueba de Conexión (Health Check)

Antes de ejecutar el proceso completo, verifica que todas las conexiones funcionen:

1. En Rocketbot, selecciona la acción **"Verificar Conexión"**
2. En el campo **"Configuración"**, pega la ruta completa a tu archivo JSON:
   ```
   C:\Ruta\A\tu\config_expedicion_copias.json
   ```
   O pega el contenido JSON directamente
3. En el campo **"Variable donde guardar resultado"**, ingresa: `resultado_health`
4. Ejecuta la acción
5. Verifica la variable `resultado_health`:

```json
{
  "crm": {
    "status": "ok",
    "message": "Conexión exitosa"
  },
  "docuware": {
    "status": "ok",
    "message": "Autenticación exitosa"
  },
  "graph": {
    "status": "ok",
    "message": "Conexión exitosa"
  },
  "database": {
    "status": "stub",
    "message": "Auditoría no implementada"
  }
}
```

**Si hay errores:**
- Verifica las credenciales en las variables de Rocketbot
- Verifica la configuración JSON
- Revisa los logs en la carpeta especificada

---

## 9. Creación de Workflows

### 9.1. Workflow Básico: Procesar Copias (Particulares)

Crea un nuevo workflow en Rocketbot:

1. **Agregar acción:** "Procesar Copias"
2. **Configurar parámetros:**
   - **Configuración:** Ruta al archivo JSON o contenido JSON
   - **Variable resultado:** `resultado_copias`
3. **Agregar lógica condicional:**
   - Si `resultado_copias.casos_procesados > 0`: Enviar notificación
   - Si `resultado_copias.casos_error > 0`: Enviar alerta

### 9.2. Workflow Básico: Procesar Copias Oficiales

Similar al anterior, pero usando la acción "Procesar Copias Oficiales".

### 9.3. Workflow Completo con Health Check

1. **Paso 1:** Verificar Conexión
   - Si falla: Enviar alerta y detener
   - Si pasa: Continuar

2. **Paso 2:** Procesar Copias
   - Guardar resultado

3. **Paso 3:** Procesar Copias Oficiales
   - Guardar resultado

4. **Paso 4:** Generar Reporte Consolidado
   - Combinar resultados de ambos procesos

### 9.4. Programación de Ejecución

Configura el workflow para ejecutarse automáticamente:

1. En Rocketbot, ve a la configuración del workflow
2. Configura un **Planificador** (Scheduler)
3. Establece la frecuencia (ej: Diario a las 8:00 AM)
4. Considera las franjas horarias configuradas en el JSON

---

## 10. Solución de Problemas

### 10.1. El Módulo No Aparece en Rocketbot

**Causas posibles:**
- El módulo no se copió correctamente
- Rocketbot no se reinició después del despliegue
- Error en `package.json`

**Solución:**
1. Verifica que la carpeta `ExpedicionCopias` existe en `[Rocketbot]/modules/`
2. Verifica que `package.json` tiene el formato correcto
3. Reinicia Rocketbot completamente
4. Revisa los logs de Rocketbot

### 10.2. Error: "Variable de Rocketbot 'graph_client_secret' no está configurada"

**Causa:** Las variables de Rocketbot no están configuradas.

**Solución:**
1. Ve a **Configuración** → **Variables**
2. Crea las variables necesarias (ver sección 3)
3. Asegúrate de usar los nombres exactos:
   - `graph_client_secret`
   - `dynamics_client_secret`
   - `docuware_password`
   - `database_password` (opcional)

### 10.3. Error de Autenticación con Dynamics 365

**Causas posibles:**
- Tenant ID o Client ID incorrectos
- Client Secret incorrecto
- La aplicación no tiene los permisos necesarios

**Solución:**
1. Verifica las credenciales en Azure Portal
2. Asegúrate de que la aplicación tiene permisos para Dynamics 365
3. Verifica que el Client Secret no haya expirado

### 10.4. Error de Autenticación con DocuWare

**Causas posibles:**
- URL incorrecta
- Username o password incorrectos
- File Cabinet ID incorrecto

**Solución:**
1. Verifica la URL del servidor DocuWare
2. Verifica las credenciales
3. Confirma el File Cabinet ID en DocuWare

### 10.5. Error: "Fuera de franja horaria o día no hábil"

**Causa:** El proceso está intentando ejecutarse fuera de las franjas horarias configuradas.

**Solución:**
1. Revisa la configuración de `FranjasHorarias` en el JSON
2. Asegúrate de incluir los días y horas correctos
3. Considera agregar más franjas si es necesario

### 10.6. No Se Descargaron Documentos

**Causas posibles:**
- No hay casos que cumplan los filtros
- Las matrículas en los casos están vacías
- Error en la búsqueda de DocuWare

**Solución:**
1. Verifica que hay casos pendientes en Dynamics 365
2. Revisa los filtros de subcategorías y especificaciones
3. Verifica que las matrículas en los casos tienen el formato correcto
4. Revisa los logs para ver errores específicos

### 10.7. Error al Enviar Email

**Causas posibles:**
- El usuario no tiene permisos para enviar emails
- El email del destinatario está vacío
- Error de conexión con Graph API

**Solución:**
1. Verifica que la aplicación tiene permisos `Mail.Send` en Graph API
2. Verifica que los casos tienen emails válidos
3. Revisa la configuración de `user_email` en GraphAPI

### 10.8. Error al Subir a OneDrive

**Causas posibles:**
- El usuario no tiene permisos en OneDrive
- La carpeta base no existe
- Error de conexión con Graph API

**Solución:**
1. Verifica que la aplicación tiene permisos `Files.ReadWrite.All` en Graph API
2. Crea la carpeta base manualmente si es necesario
3. Verifica que `user_email` tiene acceso a OneDrive

---

## 11. Monitoreo y Mantenimiento

### 11.1. Revisar Logs

Los logs se guardan en la ruta configurada en `Logs.RutaLogAuditoria`.

Revisa periódicamente:
- Errores de conexión
- Casos con errores
- Tiempos de ejecución

### 11.2. Revisar Reportes

El módulo genera reportes Excel en:
```
[Globales.RutaBaseProyecto]/reportes/reporte_expedicion_[timestamp].xlsx
```

### 11.3. Actualizar Configuración

Para actualizar la configuración:
1. Edita el archivo JSON
2. No necesitas redesplegar el módulo
3. Solo actualiza la ruta o contenido en Rocketbot

### 11.4. Actualizar el Módulo

Para actualizar el código del módulo:
1. Realiza los cambios en el código
2. Ejecuta `deploy_to_rocketbot.py` nuevamente
3. Reinicia Rocketbot

---

## 12. Mejores Prácticas

### 12.1. Seguridad

- ✅ **NUNCA** incluyas passwords o secrets en el archivo JSON
- ✅ Usa variables de Rocketbot para credenciales
- ✅ Restringe el acceso al archivo de configuración JSON
- ✅ Rota las credenciales periódicamente

### 12.2. Configuración

- ✅ Mantén una copia de respaldo del archivo de configuración
- ✅ Documenta los cambios en la configuración
- ✅ Usa un archivo de configuración por entorno (dev, test, prod)

### 12.3. Monitoreo

- ✅ Configura alertas para errores críticos
- ✅ Revisa los reportes periódicamente
- ✅ Monitorea el uso de recursos (OneDrive, emails)

### 12.4. Pruebas

- ✅ Prueba primero con pocos casos
- ✅ Verifica las conexiones antes de ejecutar procesos completos
- ✅ Prueba ambos tipos de procesamiento (Copias y Copias Oficiales)

---

## 13. Recursos Adicionales

### Documentación

- `GUIA_CREACION_MODULOS.md`: Guía completa para crear módulos
- `README.md`: Documentación general del proyecto
- Código fuente: Revisa los comentarios en el código para más detalles

### Soporte

Si encuentras problemas:
1. Revisa los logs detallados
2. Consulta la documentación
3. Verifica la configuración paso a paso
4. Contacta al equipo de desarrollo si es necesario

---

## ✅ Checklist de Implementación

- [ ] Variables de Rocketbot creadas (graph_client_secret, dynamics_client_secret, docuware_password)
- [ ] Archivo de configuración JSON creado y validado
- [ ] Módulo desplegado en Rocketbot
- [ ] Dependencias instaladas
- [ ] Rocketbot reiniciado
- [ ] Módulo visible en Rocketbot
- [ ] Health Check ejecutado exitosamente
- [ ] Workflows creados
- [ ] Pruebas iniciales realizadas
- [ ] Logs configurados y funcionando
- [ ] Monitoreo configurado

---

**¡Implementación Completada! 🎉**

El módulo ExpedicionCopias está listo para procesar casos de expedición de copias en Rocketbot.
