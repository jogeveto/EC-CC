# Configuración de ODBC Driver para SQL Server

## 📋 Tabla de Contenidos

1. [¿Por qué necesitamos ODBC Drivers?](#por-qué-necesitamos-odbc-drivers)
2. [Lógica detrás de la selección del driver](#lógica-detrás-de-la-selección-del-driver)
3. [Instalación en Linux (Ubuntu/Debian)](#instalación-en-linux-ubuntudebian)
4. [Instalación en Windows](#instalación-en-windows)
5. [Verificación de la instalación](#verificación-de-la-instalación)
6. [Errores comunes y soluciones](#errores-comunes-y-soluciones)
7. [Configuración en el código](#configuración-en-el-código)

---

## ¿Por qué necesitamos ODBC Drivers?

### Explicación técnica

**ODBC (Open Database Connectivity)** es un estándar de interfaz de programación de aplicaciones (API) que permite a las aplicaciones acceder a sistemas de gestión de bases de datos (DBMS) de manera uniforme.

Cuando usamos `pyodbc` en Python para conectarnos a SQL Server, ocurre lo siguiente:

```
┌─────────────┐         ┌──────────┐         ┌──────────────┐
│   Python    │         │  pyodbc  │         │ ODBC Driver  │
│ Application │ ──────> │  Library │ ──────> │ for SQL      │
│             │         │          │         │ Server       │
└─────────────┘         └──────────┘         └──────┬───────┘
                                                      │
                                                      ▼
                                            ┌─────────────────┐
                                            │   SQL Server    │
                                            │   (Database)     │
                                            └─────────────────┘
```

1. **pyodbc** es una biblioteca Python que implementa la interfaz ODBC
2. **ODBC Driver** es el componente del sistema operativo que traduce las llamadas ODBC a comandos específicos de SQL Server
3. **SQL Server** recibe las solicitudes a través del protocolo TDS (Tabular Data Stream)

**Sin el driver ODBC instalado**, `pyodbc` no puede comunicarse con SQL Server, resultando en errores como:
```
Can't open lib 'ODBC Driver 18 for SQL Server' : file not found
```

### ¿Por qué Driver 18 y no Driver 17?

- **Driver 17**: Versión anterior, ampliamente utilizada pero con soporte limitado en distribuciones Linux modernas
- **Driver 18**: Versión actual recomendada por Microsoft, con:
  - Mejor soporte para Ubuntu 24.04 y distribuciones recientes
  - Mejoras de seguridad (TLS 1.2+ por defecto)
  - Mejor rendimiento
  - Soporte extendido para características modernas de SQL Server

---

## Lógica detrás de la selección del driver

### Configuración por defecto

En `shared/database/connection.py`, el driver por defecto es **ODBC Driver 18 for SQL Server**:

```python
def __init__(self, server: str, database: str, user: str, password: str, 
             driver: str = "ODBC Driver 18 for SQL Server"):
```

### ¿Por qué este valor por defecto?

1. **Compatibilidad**: Driver 18 está disponible para la mayoría de sistemas operativos modernos
2. **Seguridad**: Implementa mejores prácticas de seguridad por defecto
3. **Mantenimiento**: Es la versión activamente mantenida por Microsoft
4. **Flexibilidad**: Puede ser sobrescrito si es necesario usar otra versión

### Sobrescribir el driver

Si necesitas usar un driver diferente (por ejemplo, Driver 17), puedes especificarlo en la configuración:

```python
config = {
    "db_type": "sqlserver",
    "server": "localhost",
    "database": "MyDB",
    "user": "sa",
    "password": "password",
    "driver": "ODBC Driver 17 for SQL Server"  # Sobrescribir driver
}
```

---

## Instalación en Linux (Ubuntu/Debian)

### Requisitos previos

- Ubuntu 18.04+ o Debian 9+
- Acceso sudo
- Conexión a internet

### Procedimiento paso a paso

#### Paso 1: Agregar el repositorio de Microsoft

```bash
# Agregar la clave GPG de Microsoft
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -

# Agregar el repositorio (ajusta la versión según tu Ubuntu)
# Para Ubuntu 20.04:
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

# Para Ubuntu 22.04:
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

# Para Ubuntu 24.04:
curl https://packages.microsoft.com/config/ubuntu/24.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
```

**Nota**: Si `apt-key` muestra una advertencia de deprecación, usa el método alternativo:

```bash
# Método alternativo (recomendado para Ubuntu 24.04+)
curl https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

# Actualizar el repositorio con la nueva ubicación de la clave
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/24.04/prod noble main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
```

#### Paso 2: Actualizar la lista de paquetes

```bash
sudo apt-get update
```

#### Paso 3: Instalar el driver ODBC

```bash
# Instalar ODBC Driver 18 (recomendado)
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18

# O instalar ODBC Driver 17 (si Driver 18 no está disponible)
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

**Importante**: La variable de entorno `ACCEPT_EULA=Y` acepta automáticamente el End User License Agreement (EULA) de Microsoft.

#### Paso 4: Instalar dependencias adicionales (si es necesario)

```bash
# Instalar unixODBC y herramientas de desarrollo
sudo apt-get install -y unixodbc unixodbc-dev

# Instalar herramientas de verificación (opcional)
sudo apt-get install -y odbcinst
```

### Instalación alternativa: Descarga directa del paquete .deb

Si el método del repositorio no funciona, puedes descargar e instalar el paquete directamente:

```bash
# Descargar el paquete (ajusta la versión según necesites)
wget https://packages.microsoft.com/ubuntu/24.04/prod/pool/main/m/msodbcsql18/msodbcsql18_18.5.1.1-1_amd64.deb

# Instalar el paquete
sudo ACCEPT_EULA=Y dpkg -i msodbcsql18_18.5.1.1-1_amd64.deb

# Instalar dependencias faltantes (si las hay)
sudo apt-get install -f
```

---

## Instalación en Windows

### Método 1: Instalador MSI (Recomendado)

#### Paso 1: Descargar el instalador

1. Visita la página oficial de Microsoft:
   - **ODBC Driver 18**: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
   - O busca "ODBC Driver 18 for SQL Server download" en tu navegador

2. Descarga el instalador apropiado para tu arquitectura:
   - `msodbcsql.msi` para sistemas de 64 bits
   - `msodbcsql_x64.msi` para sistemas de 64 bits (alternativo)

#### Paso 2: Ejecutar el instalador

1. Ejecuta el archivo `.msi` descargado
2. Acepta el End User License Agreement (EULA)
3. Selecciona las características a instalar (por defecto, todas están seleccionadas)
4. Completa la instalación

#### Paso 3: Verificar la instalación

1. Presiona `Win + R` y ejecuta `odbcad32.exe`
2. Ve a la pestaña **"Drivers"**
3. Busca **"ODBC Driver 18 for SQL Server"** en la lista

### Método 2: Instalación silenciosa (para scripts/automatización)

```cmd
# Descargar el instalador primero, luego ejecutar:
msiexec /i msodbcsql.msi /quiet /qn IACCEPTMSODBCSQLLICENSETERMS=YES
```

### Método 3: Usando Chocolatey (si tienes Chocolatey instalado)

```powershell
choco install msodbcsql18 -y
```

### Método 4: Usando winget (Windows Package Manager)

```powershell
winget install Microsoft.ODBCDriver18
```

---

## Verificación de la instalación

### En Linux

#### Verificar drivers instalados

```bash
# Listar todos los drivers ODBC instalados
odbcinst -q -d

# Deberías ver algo como:
# [ODBC Driver 18 for SQL Server]
```

#### Verificar configuración de ODBC

```bash
# Ver configuración de ODBC
odbcinst -j

# Salida esperada:
# unixODBC 2.3.x
# DRIVERS............: /etc/odbcinst.ini
# SYSTEM DATA SOURCES: /etc/odbc.ini
# FILE DATA SOURCES..: /etc/ODBCDataSources
# USER DATA SOURCES..: /home/user/.odbc.ini
# SQLULEN Size.......: 8
# SQLLEN Size........: 8
# SQLSETPOSIROW Size.: 8
```

#### Probar conexión (opcional)

```bash
# Instalar herramienta de prueba
sudo apt-get install -y unixodbc-bin

# Probar conexión (requiere configuración previa de DSN)
isql -v YourDSNName username password
```

### En Windows

#### Verificar drivers instalados

1. Presiona `Win + R`
2. Ejecuta `odbcad32.exe`
3. Ve a la pestaña **"Drivers"**
4. Busca **"ODBC Driver 18 for SQL Server"**

#### Verificar desde PowerShell

```powershell
# Listar drivers ODBC instalados
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"}

# Salida esperada:
# Name                                    Platform
# ----                                    --------
# ODBC Driver 18 for SQL Server           {32-bit, 64-bit}
```

---

## Errores comunes y soluciones

### Error 1: "Can't open lib 'ODBC Driver 18 for SQL Server' : file not found"

**Causa**: El driver ODBC no está instalado en el sistema.

**Solución**:
- **Linux**: Sigue los pasos de instalación en la sección [Instalación en Linux](#instalación-en-linux-ubuntudebian)
- **Windows**: Instala el driver usando el método descrito en [Instalación en Windows](#instalación-en-windows)

**Verificación**:
```bash
# Linux
odbcinst -q -d | grep -i "sql server"

# Windows
# Abre odbcad32.exe y verifica en la pestaña "Drivers"
```

### Error 2: "Unable to locate package msodbcsql18"

**Causa**: El repositorio de Microsoft no está configurado correctamente o no se actualizó.

**Solución**:
```bash
# Verificar que el repositorio está configurado
cat /etc/apt/sources.list.d/mssql-release.list

# Si está vacío o incorrecto, reconfigurar:
curl https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/24.04/prod noble main" | sudo tee /etc/apt/sources.list.d/mssql-release.list

# Actualizar lista de paquetes
sudo apt-get update

# Intentar instalar nuevamente
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

### Error 3: "SSL Provider: The target principal name is incorrect"

**Causa**: ODBC Driver 18 tiene cifrado habilitado por defecto, pero el servidor SQL Server no está configurado correctamente para SSL/TLS.

**Solución**: Agregar `TrustServerCertificate=yes` en la cadena de conexión (ya está incluido por defecto en nuestro código):

```python
connection_string = (
    f"DRIVER={{{self.driver}}};"
    f"SERVER={self.server};"
    f"DATABASE={self.database};"
    f"UID={self.user};"
    f"PWD={self.password};"
    f"TrustServerCertificate=yes;"  # Ya incluido
)
```

**Alternativa**: Si necesitas deshabilitar el cifrado completamente (no recomendado para producción):

```python
connection_string = (
    f"DRIVER={{{self.driver}}};"
    f"SERVER={self.server};"
    f"DATABASE={self.database};"
    f"UID={self.user};"
    f"PWD={self.password};"
    f"Encrypt=no;"  # Solo para desarrollo/testing
)
```

### Error 4: "No module named 'pyodbc'"

**Causa**: La biblioteca Python `pyodbc` no está instalada.

**Solución**:
```bash
# Instalar pyodbc
pip install pyodbc

# O usando uv (si estás en el proyecto)
uv pip install pyodbc
```

### Error 5: "E: Could not get lock /var/lib/apt/lists/lock"

**Causa**: Otro proceso está usando apt (por ejemplo, `apt-get update` o `apt-get install` en otra terminal).

**Solución**:
```bash
# Esperar a que termine el otro proceso, o:
# Verificar qué proceso está usando apt
sudo lsof /var/lib/apt/lists/lock

# Si es seguro, eliminar el lock (solo si estás seguro de que no hay otro proceso activo)
sudo rm /var/lib/apt/lists/lock
sudo rm /var/cache/apt/archives/lock
sudo rm /var/lib/dpkg/lock*

# Luego intentar nuevamente
sudo apt-get update
```

### Error 6: "Driver version mismatch" o problemas de arquitectura

**Causa**: El driver instalado no coincide con la arquitectura de Python (32-bit vs 64-bit).

**Solución**:
- **Linux**: Asegúrate de instalar el driver para la arquitectura correcta (amd64 para sistemas de 64 bits)
- **Windows**: Verifica que Python y el driver ODBC sean de la misma arquitectura:
  ```powershell
  # Verificar arquitectura de Python
  python -c "import platform; print(platform.architecture())"
  
  # Instalar el driver correspondiente (32-bit o 64-bit)
  ```

---

## Configuración en el código

### Uso básico

El código en `shared/database/connection.py` ya está configurado para usar ODBC Driver 18 por defecto:

```python
from shared.database.db_factory import DatabaseServiceFactory

# Uso con configuración por defecto (Driver 18)
config = {
    "db_type": "sqlserver",
    "server": "localhost",
    "database": "MyDatabase",
    "user": "sa",
    "password": "YourPassword"
}

crud = DatabaseServiceFactory.get_db_service_from_config(config)
```

### Especificar un driver diferente

Si necesitas usar un driver diferente:

```python
config = {
    "db_type": "sqlserver",
    "server": "localhost",
    "database": "MyDatabase",
    "user": "sa",
    "password": "YourPassword",
    "driver": "ODBC Driver 17 for SQL Server"  # Especificar driver diferente
}

crud = DatabaseServiceFactory.get_db_service_from_config(config)
```

### Configuración con puerto

```python
config = {
    "db_type": "sqlserver",
    "server": "localhost,1433",  # hostname,puerto
    "database": "MyDatabase",
    "user": "sa",
    "password": "YourPassword"
}
```

### Configuración para Docker

Si SQL Server está corriendo en Docker (como en este proyecto):

```python
config = {
    "db_type": "sqlserver",
    "server": "localhost",  # O la IP del contenedor
    "port": 1433,           # Puerto expuesto por Docker
    "database": "MedidasCautelares",
    "user": "SA",
    "password": "MedidasCautelares2024!"
}
```

---

## Referencias y recursos adicionales

### Documentación oficial

- **Microsoft ODBC Driver for SQL Server**: https://learn.microsoft.com/en-us/sql/connect/odbc/
- **pyodbc Documentation**: https://github.com/mkleehammer/pyodbc/wiki
- **unixODBC Documentation**: http://www.unixodbc.org/

### Enlaces de descarga

- **ODBC Driver 18 (Windows)**: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
- **ODBC Driver 18 (Linux)**: https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server

### Troubleshooting adicional

- **Microsoft Support**: https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/connection-string-keywords-and-data-source-names-dsns
- **pyodbc Issues**: https://github.com/mkleehammer/pyodbc/issues

---

## Resumen rápido

### Checklist de instalación

- [ ] **Linux**: Repositorio de Microsoft agregado
- [ ] **Linux**: `sudo apt-get update` ejecutado
- [ ] **Linux**: `msodbcsql18` instalado con `ACCEPT_EULA=Y`
- [ ] **Windows**: Instalador MSI ejecutado y EULA aceptado
- [ ] **Ambos**: `pyodbc` instalado en el entorno Python
- [ ] **Ambos**: Driver verificado con `odbcinst -q -d` (Linux) o `odbcad32.exe` (Windows)
- [ ] **Ambos**: Conexión de prueba exitosa

### Comandos rápidos

**Linux (Ubuntu 24.04)**:
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/24.04/prod noble main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
```

**Windows**:
1. Descargar e instalar desde: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
2. Verificar en `odbcad32.exe` → pestaña "Drivers"

---

**Última actualización**: Noviembre 2025  
**Versión del driver recomendada**: ODBC Driver 18 for SQL Server

