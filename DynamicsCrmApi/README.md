# DynamicsCrmApi

Módulo para consultar y actualizar PQRS en Dynamics CRM con persistencia en SQL Server.

## Descripción

Este módulo sirve como puente entre Rocketbot y Dynamics CRM, permitiendo:
- Consultar PQRS por filtros (subcategorías y especificaciones)
- Persistir los resultados en SQL Server
- Actualizar PQRS pendientes en Dynamics CRM desde la base de datos local

## Comandos Disponibles

### 1. Consultar por Filtros (`consultar_por_filtros`)

Consulta PQRS desde Dynamics CRM usando filtros de subcategorías y especificaciones, y persiste los resultados en SQL Server.

**Variables Requeridas:**
- `config`: Configuración JSON con `database` (configuración de SQL Server)
- `subcategorias_ids`: JSON string con array de IDs de subcategorías (ej: `["id1", "id2"]`)
- `subcategoria_name`: Nombre de la subcategoría (ej: "COPIAS" o "COPIAS ENTIDADES OFICIALES")
- `dynamics_tenant_id`: Tenant ID de Azure AD
- `dynamics_client_id`: Client ID de la aplicación
- `dynamics_client_secret`: Client Secret (valor del secret)
- `dynamics_url`: URL base de Dynamics CRM (ej: `https://ccmadev.crm2.dynamics.com/api/data/v9.2`)

**Variables Opcionales:**
- `invt_especificacion`: JSON string con array de IDs de especificaciones

**Resultado:**
```json
{
    "status": "success",
    "message": "Consulta completada exitosamente",
    "registros_encontrados": 10,
    "registros_guardados": 10,
    "subcategoria_name": "COPIAS"
}
```

### 2. Actualizar PQRS (`actualizar_pqrs`)

Actualiza PQRS pendientes en Dynamics CRM desde la base de datos local. Lee registros donde `actualizadoCRM = false` y `subcategoriaName` coincide, actualiza en CRM y marca como actualizado.

**Variables Requeridas:**
- `config`: Configuración JSON con `database`
- `subcategoria_name`: Nombre de la subcategoría a filtrar
- `dynamics_tenant_id`: Tenant ID de Azure AD
- `dynamics_client_id`: Client ID de la aplicación
- `dynamics_client_secret`: Client Secret
- `dynamics_url`: URL base de Dynamics CRM

**Resultado:**
```json
{
    "status": "success",
    "message": "Actualización completada",
    "registros_procesados": 5,
    "registros_actualizados": 5
}
```

### 3. Health Check (`health_check`)

Verifica la conexión con la base de datos.

**Variables Requeridas:**
- `config`: Configuración JSON con `database`

## Estructura de Base de Datos

### Tabla: `ExpedicionCopiasDbo.expedicion_copias_pqrs`

La tabla almacena todos los campos del JSON de respuesta de Dynamics CRM más campos adicionales para el proceso de expedición.

**Campos Principales:**
- `sp_documentoid` (PK): ID único del documento
- `sp_name`: Número de PQRS (ej: "PQRS-0016292")
- `sp_titulopqrs`: Título de la PQRS
- `sp_descripcion`: Descripción
- `sp_descripciondelasolucion`: Descripción de la solución
- `sp_resolvercaso`: Indica si el caso está resuelto

**Campos Extra (Proceso de Expedición):**
- `subcategoriaName`: Nombre de la subcategoría de búsqueda
- `BusquedaDocumentos`: Boolean
- `CantDocumentos`: Integer
- `UnionDocumentos`: Boolean
- `alamcenadoDocumentos`: Boolean
- `envioCorreo`: Boolean
- `cuerpoCorreo`: Texto del cuerpo del correo
- `actualizadoCRM`: Boolean (indica si ya fue actualizado en CRM)

**Campos de Auditoría:**
- `fecha_creacion`: Fecha de creación del registro
- `fecha_edicion`: Fecha de última edición (actualizada automáticamente por trigger)

**Script SQL:**
Ver `DB/init/02-create-dynamics-crm-pqrs-table.sql` para la definición completa de la tabla, índices y triggers.

## Configuración

### Configuración de Base de Datos

El parámetro `config` debe incluir la configuración de SQL Server:

```json
{
    "database": {
        "db_type": "sqlserver",
        "server": "servidor,1433",
        "database": "RPA_Automatizacion",
        "user": "usuario",
        "password": "contraseña"
    },
    "Logs": {
        "RutaLogAuditoria": "C:\\logs",
        "NombreLogAuditoria": "dynamics_crm_api.log"
    },
    "Globales": {
        "RutaBaseProyecto": "C:\\proyecto"
    }
}
```

## Dependencias

### Librerías Requeridas

- `azure-identity`: Para autenticación con Azure AD
- `azure-core`: Dependencia de `azure-identity`
- `requests`: Para peticiones HTTP a Dynamics CRM
- `shared`: Utilidades compartidas del proyecto (logger, database factory, etc.)

### Instalación de Dependencias

Las librerías de Azure (`azure-identity` y `azure-core`) deben estar disponibles en el entorno de Python de Rocketbot. Tienes dos opciones:

#### Opción 1: Instalación Global (Recomendado)

Instala las dependencias globalmente en el entorno de Python de Rocketbot:

```bash
pip install azure-identity azure-core requests
```

#### Opción 2: Librerías Vendored (Carpeta `libs/`)

Si prefieres incluir las librerías con el módulo, puedes crear la carpeta `libs/` dentro de `DynamicsCrmApi/` y copiar allí las librerías de Azure. El módulo detectará automáticamente esta carpeta si existe.

**Nota importante**: Si copias manualmente la carpeta `DynamicsCrmApi` a Rocketbot, asegúrate de:
- Copiar también la carpeta `libs/` si existe, O
- Instalar las dependencias globalmente en Python de Rocketbot

El módulo verificará automáticamente si existe la carpeta `libs/` y la usará si está disponible. Si no existe, intentará usar las librerías instaladas globalmente.

## Arquitectura

```
Rocketbot → DynamicsCrmApi/__init__.py → Services → Core (Dynamics Client) → Dynamics CRM API
                                                      ↓
                                              Database (SQL Server)
```

## Logging

El módulo utiliza el sistema de logging de `shared`, registrando:
- Inicio y fin de operaciones
- Errores con stack traces
- Información de debug (paginación, registros procesados, etc.)

Los logs se guardan según la configuración en `config.Logs`.

## Manejo de Errores

El módulo maneja errores de forma robusta:
- Validación de variables requeridas
- Manejo de errores de autenticación con mensajes descriptivos
- Manejo de errores de conexión a BD
- Logging detallado de errores

## Notas

- Las credenciales de Dynamics CRM se proporcionan como variables de Rocketbot (no desde archivos locales)
- La búsqueda implementa paginación recursiva completa para obtener todos los registros
- Los registros se insertan o actualizan según si ya existen en BD (basado en `sp_documentoid`)
