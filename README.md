# Proyecto Expedición de Copias

Proyecto modular para Rocketbot basado en la arquitectura de Medidas-Cautelares.

## 📁 Estructura del Proyecto

```
Expedicion-copias/
├── shared/                    # Módulo transversal (Framework base)
│   ├── core/                  # Interfaces y clases base
│   ├── database/              # Gestión de conexiones BD
│   └── utils/                 # Utilidades comunes
│
├── ExpedicionCopias/          # Módulo principal de negocio
│   ├── __init__.py            # Punto de entrada Rocketbot
│   ├── package.json           # Configuración Rocketbot
│   ├── core/                  # Lógica pura (scrapers, procesadores)
│   ├── services/              # Orquestación de negocio
│   └── libs/                  # Dependencias locales
│
├── DB/                        # Configuración de base de datos
│   ├── docker-compose.yml     # Contenedor SQL Server
│   └── init/                  # Scripts SQL de inicialización
│
├── rocketbot_scripts/         # Scripts auxiliares para workflows
├── deploy_to_rocketbot.py     # Script de despliegue
└── requirements.txt          # Dependencias globales
```

## 🎯 Arquitectura

Este proyecto sigue los principios SOLID y utiliza una arquitectura modular:

- **`shared/`**: Framework base con clases abstractas y utilidades compartidas
- **`ExpedicionCopias/`**: Módulo de negocio (estructura lista para implementar)
- **`DB/`**: Infraestructura de base de datos con Docker

## 🚀 Inicio Rápido

### 1. Configurar Base de Datos

```bash
cd DB
docker-compose up -d
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Desplegar a Rocketbot

```bash
python deploy_to_rocketbot.py
```

## 📝 Estado del Proyecto

Este proyecto está en estado inicial. El módulo `ExpedicionCopias` tiene la estructura base lista pero requiere implementación de la lógica de negocio específica.

### Módulos Implementados

- ✅ **shared/**: Framework completo
- ✅ **DB/**: Configuración de base de datos
- ✅ **ExpedicionCopias/**: Estructura base (lista para desarrollo)

### Próximos Pasos

1. Implementar lógica de negocio en `ExpedicionCopias/core/`
2. Crear servicios de orquestación en `ExpedicionCopias/services/`
3. Definir esquema de base de datos en `DB/init/`
4. Configurar workflows en Rocketbot

## 🔧 Desarrollo

### Estructura de un Módulo

Cada módulo sigue esta estructura:

- **`core/`**: Implementaciones que extienden clases base de `shared/`
- **`services/`**: Lógica de negocio que orquesta componentes de `core/`
- **`__init__.py`**: Punto de entrada que mantiene compatibilidad con Rocketbot

### Usar Shared desde el Módulo

```python
import os
import sys

base_path = tmp_global_obj["basepath"]
shared_path = base_path + "modules" + os.sep + "shared" + os.sep
if shared_path not in sys.path:
    sys.path.append(shared_path)

from database.db_factory import DatabaseServiceFactory
from utils.logger import setup_logger
```

## 📚 Referencias

- **📖 [GUIA_CREACION_MODULOS.md](GUIA_CREACION_MODULOS.md)**: Guía completa para crear módulos desde cero
- Ver `Medidas-Cautelares/README.md` para documentación completa de la arquitectura
- Consultar `shared/` para ver las clases base disponibles
- Revisar `ExpedicionCopias/__init__.py` para ver el template de punto de entrada

