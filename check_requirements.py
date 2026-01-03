#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para verificar requisitos del modulo DynamicsCrmApi"""

import sys
import platform

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("VERIFICACION DE REQUISITOS - DynamicsCrmApi")
print("=" * 60)
print()

# 1. Python
print("1. PYTHON")
print(f"   Version: {platform.python_version()}")
print(f"   Arquitectura: {platform.architecture()[0]}")
print()

# 2. pyodbc
print("2. pyodbc (Libreria Python para ODBC)")
try:
    import pyodbc
    print(f"   [OK] INSTALADO - Version: {pyodbc.version}")
    drivers = pyodbc.drivers()
    print(f"   Drivers ODBC detectados por pyodbc: {len(drivers)}")
    sql_drivers = [d for d in drivers if "SQL Server" in d]
    if sql_drivers:
        print(f"   [OK] Drivers SQL Server encontrados:")
        for driver in sql_drivers:
            print(f"      - {driver}")
    else:
        print(f"   [ERROR] NO se encontraron drivers SQL Server")
except ImportError:
    print("   [ERROR] NO INSTALADO")
print()

# 3. Librerias de Azure
print("3. LIBRERIAS DE AZURE")
try:
    import azure.identity
    print("   [OK] azure-identity: INSTALADO")
except ImportError:
    print("   [ERROR] azure-identity: NO INSTALADO")

try:
    import azure.core
    print("   [OK] azure-core: INSTALADO")
except ImportError:
    print("   [ERROR] azure-core: NO INSTALADO")
print()

# 4. requests
print("4. requests (HTTP)")
try:
    import requests
    print(f"   [OK] INSTALADO - Version: {requests.__version__}")
except ImportError:
    print("   [ERROR] NO INSTALADO")
print()

# 5. Resumen
print("=" * 60)
print("RESUMEN")
print("=" * 60)

all_ok = True
issues = []

# Verificar pyodbc
try:
    import pyodbc
    drivers = pyodbc.drivers()
    sql_drivers = [d for d in drivers if "SQL Server" in d]
    if not sql_drivers:
        all_ok = False
        issues.append("[ERROR] pyodbc no detecta drivers SQL Server (aunque el driver este instalado)")
except ImportError:
    all_ok = False
    issues.append("[ERROR] pyodbc NO esta instalado")

# Verificar azure
try:
    import azure.identity
    import azure.core
except ImportError:
    all_ok = False
    issues.append("[ERROR] Librerias de Azure NO estan instaladas")

# Verificar requests
try:
    import requests
except ImportError:
    all_ok = False
    issues.append("[ERROR] requests NO esta instalado")

if all_ok and len(issues) == 0:
    print("[OK] TODOS LOS REQUISITOS ESTAN CUMPLIDOS")
    print()
    print("Tu maquina esta lista para ejecutar DynamicsCrmApi")
else:
    print("[ADVERTENCIA] SE ENCONTRARON PROBLEMAS:")
    for issue in issues:
        print(f"   {issue}")
    print()
    print("Consulta la documentacion en:")
    print("   - shared/database/README_ODBC_SETUP.md")
    print("   - shared/database/ODBC_QUICK_REFERENCE.md")
    print("   - DynamicsCrmApi/README.md")

print()
print("=" * 60)
