# Guía Completa: Creación de Módulos desde Cero

Esta guía te enseñará cómo crear un módulo completo para Rocketbot desde cero, siguiendo la arquitectura del proyecto **Expedicion-copias**.

---

## 📋 Tabla de Contenidos

1. [Arquitectura del Módulo](#arquitectura-del-módulo)
2. [Estructura de Carpetas](#estructura-de-carpetas)
3. [Creación del `__init__.py`](#creación-del-__init__py)
4. [Creación del `package.json`](#creación-del-packagejson)
5. [Integración con Rocketbot](#integración-con-rocketbot)
6. [Uso del Framework `shared`](#uso-del-framework-shared)
7. [Patrones de Desarrollo](#patrones-de-desarrollo)
8. [Testing](#testing)
9. [Despliegue](#despliegue)
10. [Ejemplo Completo](#ejemplo-completo)

---

## 🏗️ Arquitectura del Módulo

### Principios Fundamentales

Cada módulo debe seguir estos principios:

1. **Separación de Responsabilidades**: `core/` para lógica pura, `services/` para orquestación
2. **Dependencia de Abstracciones**: Usar `shared/` en lugar de implementaciones directas
3. **Compatibilidad con Rocketbot**: El `__init__.py` debe manejar `GetParams`, `SetVar`, etc.
4. **Logging Centralizado**: Usar el logger de `shared/utils/logger`
5. **Configuración Flexible**: Aceptar JSON o diccionarios Python

### Flujo de Ejecución

```
Rocketbot → __init__.py → Service → Core Components → Database/External APIs
```

---

## 📁 Estructura de Carpetas

### Estructura Mínima Requerida

```
MiModulo/
├── __init__.py              # Punto de entrada Rocketbot (OBLIGATORIO)
├── package.json             # Configuración Rocketbot (OBLIGATORIO)
├── core/                    # Lógica pura del módulo
│   ├── __init__.py
│   └── [componentes].py     # Extractores, procesadores, validadores
├── services/                 # Orquestación de negocio
│   ├── __init__.py
│   └── [servicios].py       # Servicios que coordinan componentes
└── libs/                     # Dependencias locales (opcional)
```

### Estructura Recomendada Completa

```
MiModulo/
├── __init__.py
├── package.json
├── README.md                 # Documentación del módulo
├── requirements.txt          # Dependencias específicas (opcional)
├── core/
│   ├── __init__.py
│   ├── extractor.py         # Extracción de datos
│   ├── processor.py         # Procesamiento de datos
│   └── validator.py         # Validación de datos
├── services/
│   ├── __init__.py
│   ├── main_service.py      # Servicio principal
│   └── db_service.py        # Acceso a base de datos
├── libs/                     # Dependencias locales
└── tests/                    # Tests unitarios (opcional)
    ├── __init__.py
    └── test_*.py
```

---

## 📝 Creación del `__init__.py`

### Template Base

El `__init__.py` es el punto de entrada que Rocketbot ejecuta. Debe seguir este patrón:

```python
# coding: utf-8
"""
Módulo MiModulo para Rocketbot.
Descripción breve del módulo.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Any

# ============================================
# CONFIGURACIÓN DE PATHS (NO MODIFICAR)
# ============================================
try:
    tmp_global_obj  # type: ignore[name-defined]
except NameError:  # pragma: no cover
    tmp_global_obj = {"basepath": ""}
    
    def GetParams(_):  # noqa: D401, N802
        return None
    
    def SetVar(_, __):  # noqa: D401, N802
        return None
    
    def PrintException():  # noqa: D401, N802
        return None

base_path = tmp_global_obj["basepath"]
modules_path = base_path + "modules" + os.sep
shared_path = modules_path + "shared" + os.sep
mi_modulo_path = modules_path + "MiModulo" + os.sep
libs_path = mi_modulo_path + "libs" + os.sep

# Agregar paths al sys.path
if modules_path not in sys.path:
    sys.path.insert(0, modules_path)
if shared_path not in sys.path:
    sys.path.append(shared_path)
if mi_modulo_path not in sys.path:
    sys.path.insert(0, mi_modulo_path)
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

# ============================================
# IMPORTS DE SHARED
# ============================================
import logging
from shared.utils.logger import get_logger
from shared.utils.config_helper import load_config_from_param
from shared.database.db_factory import DatabaseServiceFactory

# ============================================
# CONFIGURACIÓN DEL LOGGER
# ============================================
logger = get_logger("MiModulo")
_logger_configurado = False

def _inicializar_logger_modulo(config: Dict[str, Any]) -> None:
    """Configura el logger del módulo."""
    global _logger_configurado, logger
    
    if _logger_configurado:
        return
    
    logs_config = config.get("Logs")
    ruta_base = config.get("Globales", {}).get("RutaBaseProyecto")
    
    config_para_logger = None
    if logs_config and isinstance(logs_config, dict):
        ya_normalizado = "auditoria" in logs_config or "sistema" in logs_config
        if ya_normalizado:
            config_para_logger = logs_config
        else:
            config_para_logger = {
                "Logs": logs_config,
                "Globales": {"RutaBaseProyecto": ruta_base} if ruta_base else {}
            }
    elif ruta_base:
        config_para_logger = {
            "Logs": {},
            "Globales": {"RutaBaseProyecto": ruta_base}
        }
    
    try:
        from shared.utils.logger import establecer_configuracion_global
        establecer_configuracion_global(config_para_logger, ruta_base)
    except (ImportError, AttributeError):
        pass
    
    try:
        from shared.utils.logger import setup_logger
        logger_obj = setup_logger("MiModulo", logs_config=config_para_logger, ruta_base=ruta_base)
        logger = logger_obj
    except Exception:
        pass
    
    _logger_configurado = True

# ============================================
# PUNTO DE ENTRADA ROCKETBOT
# ============================================
module = GetParams("module")

try:
    if module == "accion_principal":
        logger.info("[INICIO] Ejecutando acción principal")
        config_param = GetParams("config")
        result_var = GetParams("result")
        
        try:
            # Cargar configuración
            config = load_config_from_param(config_param) if config_param else {}
            _inicializar_logger_modulo(config)
            
            # Importar y ejecutar servicio
            from MiModulo.services.main_service import MainService
            service = MainService(config)
            resultado = service.ejecutar_accion_principal()
            
            logger.info(f"[FIN] Acción completada: {resultado.get('status')}")
            if result_var:
                SetVar(result_var, resultado)
                
        except Exception as e:
            error_msg = f"Error en acción principal: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            resultado = {"status": "error", "message": error_msg}
            if result_var:
                SetVar(result_var, resultado)
            PrintException()
            raise e
    
    elif module == "health_check":
        logger.info("[INICIO] Health check")
        config_param = GetParams("config")
        result_var = GetParams("result")
        
        try:
            config = load_config_from_param(config_param) if config_param else {}
            _inicializar_logger_modulo(config)
            
            db_config = config.get("database", {})
            if not db_config:
                result = {
                    "status": "error",
                    "message": "No se encontró configuración de base de datos",
                }
            else:
                try:
                    crud = DatabaseServiceFactory.get_db_service_from_config(db_config.copy())
                    result = {
                        "status": "ok",
                        "message": "Conexión a base de datos exitosa",
                        "db_type": db_config.get("db_type", "unknown"),
                    }
                except Exception as db_error:
                    result = {
                        "status": "error",
                        "message": f"Error de conexión: {str(db_error)}",
                    }
            
            if result_var:
                SetVar(result_var, result)
            logger.info(f"[FIN] Health check: {result.get('status')}")
            
        except Exception as e:
            error_msg = f"Error en health check: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            result = {"status": "error", "message": error_msg}
            if result_var:
                SetVar(result_var, result)
            PrintException()
            raise e

except Exception as e:
    logger.error(f"Error en módulo MiModulo: {e}")
    PrintException()
    raise e
```

### Puntos Clave del `__init__.py`

1. **Manejo de `tmp_global_obj`**: Permite ejecución fuera de Rocketbot (tests)
2. **Configuración de Paths**: Agrega `shared/` y el módulo actual al path
3. **Inicialización del Logger**: Configuración única y reutilizable
4. **Routing de Comandos**: Usa `GetParams("module")` para enrutar acciones
5. **Manejo de Errores**: Try/except con logging y `PrintException()`
6. **Retorno de Resultados**: Usa `SetVar()` para devolver resultados

---

## 📦 Creación del `package.json`

### Template Base

```json
{
    "author": "Tu Equipo",
    "description": "Descripción breve del módulo",
    "description_lang": {
        "es": "Descripción en español",
        "en": "Description in English",
        "pr": "Descrição em português"
    },
    "disclaimer": "THERE IS NO WARRANTY FOR THE PROGRAM...",
    "version": "1.0.0",
    "license": "MIT",
    "homepage": "http://rocketbot.com",
    "linux": true,
    "windows": true,
    "mac": true,
    "docker": true,
    "name": "MiModulo",
    "dependencies": {
        "libreria1": "^1.0.0",
        "libreria2": "^2.0.0"
    },
    "title": {
        "en": "My Module",
        "es": "Mi Módulo",
        "pr": "Meu Módulo"
    },
    "icon": "data:image/png;base64,...",
    "children": [
        {
            "en": {
                "title": "Main Action",
                "description": "Description of main action",
                "title_options": "Select Option",
                "options": null
            },
            "es": {
                "title": "Acción Principal",
                "description": "Descripción de la acción principal",
                "title_options": "Seleccione una opción",
                "options": null
            },
            "pr": {
                "title": "Ação Principal",
                "description": "Descrição da ação principal",
                "title_options": "Selecione uma opção",
                "options": null
            },
            "form": {
                "css": "modal-lg",
                "inputs": [
                    {
                        "type": "textarea",
                        "placeholder": {
                            "es": "Ruta a archivo JSON o diccionario con configuración",
                            "en": "Path to JSON file or dictionary with configuration",
                            "pr": "Caminho para arquivo JSON ou dicionário com configuração"
                        },
                        "title": {
                            "es": "Configuración",
                            "en": "Configuration",
                            "pr": "Configuração"
                        },
                        "id": "config",
                        "css": "col-md-12"
                    },
                    {
                        "type": "input",
                        "placeholder": {
                            "es": "Variable",
                            "en": "Variable",
                            "pr": "Variável"
                        },
                        "title": {
                            "es": "Variable donde guardar resultado",
                            "en": "Variable to store result",
                            "pr": "Variável para armazenar resultado"
                        },
                        "remove_vars": true,
                        "id": "result",
                        "css": "col-md-12"
                    }
                ]
            },
            "icon": "data:image/png;base64,...",
            "module": "accion_principal",
            "module_name": "MiModulo",
            "visible": true,
            "options": false,
            "linux": true,
            "windows": true,
            "mac": true,
            "docker": true,
            "father": "module",
            "group": "scripts"
        },
        {
            "en": {
                "title": "Health Check",
                "description": "Verifies connection status",
                "title_options": "Select Option",
                "options": null
            },
            "es": {
                "title": "Verificar Conexión",
                "description": "Verifica el estado de conexión",
                "title_options": "Seleccione una opción",
                "options": null
            },
            "pr": {
                "title": "Verificar Conexão",
                "description": "Verifica o status da conexão",
                "title_options": "Selecione uma opção",
                "options": null
            },
            "form": {
                "css": "modal-lg",
                "inputs": [
                    {
                        "type": "textarea",
                        "placeholder": {
                            "es": "Configuración",
                            "en": "Configuration",
                            "pr": "Configuração"
                        },
                        "title": {
                            "es": "Configuración",
                            "en": "Configuration",
                            "pr": "Configuração"
                        },
                        "id": "config",
                        "css": "col-md-12"
                    },
                    {
                        "type": "input",
                        "placeholder": {
                            "es": "Variable",
                            "en": "Variable",
                            "pr": "Variável"
                        },
                        "title": {
                            "es": "Variable donde guardar resultado",
                            "en": "Variable to store result",
                            "pr": "Variável para armazenar resultado"
                        },
                        "remove_vars": true,
                        "id": "result",
                        "css": "col-md-12"
                    }
                ]
            },
            "icon": "data:image/png;base64,...",
            "module": "health_check",
            "module_name": "MiModulo",
            "visible": true,
            "options": false,
            "linux": true,
            "windows": true,
            "mac": true,
            "docker": true,
            "father": "module",
            "group": "scripts"
        }
    ]
}
```

### Campos Importantes

- **`name`**: Debe coincidir con el nombre de la carpeta del módulo
- **`module`**: Debe coincidir con el valor que se compara en `GetParams("module")`
- **`module_name`**: Debe ser igual a `name`
- **`children`**: Array de acciones disponibles en Rocketbot
- **`form.inputs`**: Define los campos del formulario en Rocketbot

---

## 🔌 Integración con Rocketbot

### Flujo de Ejecución

1. **Rocketbot carga el módulo**: Lee `package.json` y muestra acciones en la UI
2. **Usuario selecciona acción**: Rocketbot ejecuta `__init__.py` con `module = "accion_principal"`
3. **Módulo procesa**: Lee parámetros con `GetParams()`, ejecuta lógica, retorna con `SetVar()`

### Parámetros Estándar

```python
# Obtener parámetros
module = GetParams("module")           # Nombre de la acción
config = GetParams("config")           # Configuración (JSON o dict)
result_var = GetParams("result")      # Variable donde guardar resultado
limit = GetParams("limit")            # Límite de registros (opcional)

# Retornar resultados
SetVar(result_var, {
    "status": "success",
    "message": "Procesamiento completado",
    "data": {...}
})
```

### Manejo de Configuración

```python
from shared.utils.config_helper import load_config_from_param

# Acepta JSON string o diccionario Python
config = load_config_from_param(config_param)

# Estructura típica:
config = {
    "database": {
        "db_type": "sqlserver",
        "host": "localhost",
        "port": 1433,
        "database": "MiBaseDatos",
        "user": "SA",
        "password": "password"
    },
    "Logs": {
        "RutaLogAuditoria": "C:\\logs",
        "NombreLogAuditoria": "mi_modulo.log"
    },
    "Globales": {
        "RutaBaseProyecto": "C:\\proyecto"
    }
}
```

---

## 🛠️ Uso del Framework `shared`

### Database Factory

```python
from shared.database.db_factory import DatabaseServiceFactory

# Obtener servicio CRUD
db_config = config.get("database", {})
crud = DatabaseServiceFactory.get_db_service_from_config(db_config.copy())

# Ejecutar consultas
result = crud.execute_query("SELECT * FROM tabla WHERE id = ?", (1,))
crud.execute_non_query("INSERT INTO tabla (col) VALUES (?)", ("valor",))
```

### Logger

```python
from shared.utils.logger import get_logger, setup_logger

# Obtener logger
logger = get_logger("MiModulo")

# Usar logger
logger.info("Mensaje informativo")
logger.warning("Advertencia")
logger.error("Error", exc_info=True)
logger.debug("Debug")
```

### Validadores

```python
from shared.utils.validators import validate_email, validate_url

if validate_email(email):
    # Email válido
    pass
```

### Helpers

```python
from shared.utils.helpers import format_date, safe_get

fecha = format_date(datetime.now())
valor = safe_get(diccionario, "clave", "default")
```

---

## 🎯 Patrones de Desarrollo

### Patrón Service Layer

```python
# services/main_service.py
from typing import Dict, Any
from shared.utils.logger import get_logger
from MiModulo.core.extractor import Extractor
from MiModulo.core.validator import Validator

logger = get_logger("MainService")

class MainService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.extractor = Extractor()
        self.validator = Validator()
    
    def ejecutar_accion_principal(self) -> Dict[str, Any]:
        try:
            # 1. Extraer datos
            datos = self.extractor.extraer()
            
            # 2. Validar
            if not self.validator.validar(datos):
                return {"status": "error", "message": "Datos inválidos"}
            
            # 3. Procesar
            resultado = self.procesar(datos)
            
            return {
                "status": "success",
                "message": "Procesamiento exitoso",
                "data": resultado
            }
        except Exception as e:
            logger.error(f"Error en ejecutar_accion_principal: {e}", exc_info=True)
            raise
```

### Patrón Repository (Base de Datos)

```python
# services/db_service.py
from shared.database.db_factory import DatabaseServiceFactory
from typing import List, Dict, Any

class DbService:
    def __init__(self, db_config: Dict[str, Any]):
        self.crud = DatabaseServiceFactory.get_db_service_from_config(db_config.copy())
    
    def obtener_registros_pendientes(self) -> List[Dict[str, Any]]:
        query = """
            SELECT id, campo1, campo2
            FROM tabla
            WHERE estado = 'PENDIENTE'
        """
        return self.crud.execute_query(query)
    
    def actualizar_estado(self, id: int, estado: str) -> None:
        query = "UPDATE tabla SET estado = ? WHERE id = ?"
        self.crud.execute_non_query(query, (estado, id))
```

### Patrón Extractor

```python
# core/extractor.py
from typing import Dict, Any, Optional
import re

class Extractor:
    def extraer_desde_texto(self, texto: str) -> Optional[Dict[str, Any]]:
        """Extrae información usando regex."""
        patron = r"(\d{8})"
        match = re.search(patron, texto)
        if match:
            return {"radicado": match.group(1)}
        return None
```

### Patrón Validator

```python
# core/validator.py
from typing import Dict, Any

class Validator:
    def __init__(self, min_digits: int = 8):
        self.min_digits = min_digits
    
    def validar(self, datos: Dict[str, Any]) -> bool:
        """Valida los datos extraídos."""
        if "radicado" not in datos:
            return False
        return len(datos["radicado"]) >= self.min_digits
```

---

## 🧪 Testing

### Estructura de Tests

```python
# tests/test_main_service.py
import unittest
from MiModulo.services.main_service import MainService

class TestMainService(unittest.TestCase):
    def setUp(self):
        self.config = {
            "database": {
                "db_type": "sqlite",
                "database": ":memory:"
            }
        }
        self.service = MainService(self.config)
    
    def test_ejecutar_accion_principal(self):
        resultado = self.service.ejecutar_accion_principal()
        self.assertEqual(resultado["status"], "success")
```

### Ejecutar Tests

```bash
python -m pytest tests/ -v
```

---

## 🚀 Despliegue

### Actualizar `deploy_to_rocketbot.py`

Agregar tu módulo a la lista:

```python
MODULES_TO_DEPLOY = ["MiModulo"]
```

### Ejecutar Despliegue

```bash
python deploy_to_rocketbot.py
```

Esto copiará tu módulo a la carpeta `modules/` de Rocketbot.

---

## 📚 Ejemplo Completo

### Módulo: `ProcesadorDocumentos`

#### Estructura

```
ProcesadorDocumentos/
├── __init__.py
├── package.json
├── core/
│   ├── __init__.py
│   ├── pdf_reader.py
│   └── text_extractor.py
└── services/
    ├── __init__.py
    └── document_service.py
```

#### `core/pdf_reader.py`

```python
import pdfplumber
from typing import Optional

class PdfReader:
    def leer_pdf(self, ruta: str) -> Optional[str]:
        try:
            with pdfplumber.open(ruta) as pdf:
                texto = ""
                for page in pdf.pages:
                    texto += page.extract_text() or ""
                return texto
        except Exception:
            return None
```

#### `services/document_service.py`

```python
from typing import Dict, Any
from shared.utils.logger import get_logger
from ProcesadorDocumentos.core.pdf_reader import PdfReader

logger = get_logger("DocumentService")

class DocumentService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pdf_reader = PdfReader()
    
    def procesar_documento(self, ruta: str) -> Dict[str, Any]:
        texto = self.pdf_reader.leer_pdf(ruta)
        if not texto:
            return {"status": "error", "message": "No se pudo leer el PDF"}
        
        return {
            "status": "success",
            "texto": texto,
            "longitud": len(texto)
        }
```

#### `__init__.py` (fragmento)

```python
if module == "procesar_documento":
    logger.info("[INICIO] Procesando documento")
    config_param = GetParams("config")
    ruta_param = GetParams("ruta")
    result_var = GetParams("result")
    
    try:
        config = load_config_from_param(config_param) if config_param else {}
        _inicializar_logger_modulo(config)
        
        from ProcesadorDocumentos.services.document_service import DocumentService
        service = DocumentService(config)
        resultado = service.procesar_documento(ruta_param)
        
        if result_var:
            SetVar(result_var, resultado)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        PrintException()
        raise e
```

---

## ✅ Checklist de Creación

- [ ] Crear estructura de carpetas (`core/`, `services/`, `libs/`)
- [ ] Crear `__init__.py` con template base
- [ ] Crear `package.json` con metadatos
- [ ] Implementar componentes en `core/`
- [ ] Implementar servicios en `services/`
- [ ] Integrar con `shared/` (logger, database, etc.)
- [ ] Agregar manejo de errores robusto
- [ ] Crear tests unitarios
- [ ] Documentar en `README.md`
- [ ] Actualizar `deploy_to_rocketbot.py`
- [ ] Probar en Rocketbot

---

## 🔗 Referencias

- Ver `ExpedicionCopias/__init__.py` para ejemplo real
- Ver `CapturaInformacion/` en `Medidas-Cautelares/` para módulo completo
- Consultar `shared/` para utilidades disponibles
- Revisar `rocketbot_scripts/README.md` para scripts auxiliares

---

## 📞 Soporte

Para dudas o problemas:
1. Revisa esta guía
2. Consulta módulos existentes como referencia
3. Revisa los logs del módulo
4. Contacta al equipo de desarrollo

---

**¡Feliz desarrollo! 🚀**





