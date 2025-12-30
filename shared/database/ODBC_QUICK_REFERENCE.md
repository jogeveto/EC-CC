# ODBC Driver - Referencia Rápida

## 🚀 Instalación Rápida

### Linux (Ubuntu 24.04)

```bash
# 1. Agregar repositorio
curl https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/ubuntu/24.04/prod noble main" | sudo tee /etc/apt/sources.list.d/mssql-release.list

# 2. Actualizar e instalar
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev

# 3. Verificar
odbcinst -q -d | grep -i "sql server"
```

### Windows

1. Descargar: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
2. Ejecutar el instalador `.msi`
3. Verificar: `Win + R` → `odbcad32.exe` → pestaña "Drivers"

## ✅ Verificación

```bash
# Linux
odbcinst -q -d

# Windows
# Abrir odbcad32.exe y verificar en pestaña "Drivers"
```

## 🔧 Errores Comunes

| Error | Solución |
|-------|----------|
| `Can't open lib 'ODBC Driver 18'` | Instalar el driver (ver arriba) |
| `Unable to locate package msodbcsql18` | Ejecutar `sudo apt-get update` |
| `SSL Provider: The target principal name is incorrect` | Ya resuelto con `TrustServerCertificate=yes` |
| `No module named 'pyodbc'` | `pip install pyodbc` |

## 📝 Uso en Código

```python
from shared.database.db_factory import DatabaseServiceFactory

config = {
    "db_type": "sqlserver",
    "server": "localhost",
    "database": "MyDB",
    "user": "sa",
    "password": "password"
}

crud = DatabaseServiceFactory.get_db_service_from_config(config)
```

## 📚 Documentación Completa

Para detalles completos, consulta: **`README_ODBC_SETUP.md`**

