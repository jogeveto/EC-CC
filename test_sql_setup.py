#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para verificar la configuracion de SQL Server sin conectar"""

import pyodbc

print("=" * 60)
print("VERIFICACION DE CONFIGURACION SQL SERVER")
print("=" * 60)
print()

# 1. Verificar pyodbc
print("1. pyodbc")
try:
    print(f"   [OK] Version: {pyodbc.version}")
except:
    print("   [ERROR] pyodbc no disponible")
    sys.exit(1)

# 2. Listar drivers disponibles
print()
print("2. Drivers ODBC disponibles")
drivers = pyodbc.drivers()
print(f"   Total de drivers: {len(drivers)}")
print()

sql_drivers = [d for d in drivers if "SQL Server" in d]
if sql_drivers:
    print("   [OK] Drivers SQL Server encontrados:")
    for i, driver in enumerate(sql_drivers, 1):
        print(f"      {i}. {driver}")
else:
    print("   [ERROR] No se encontraron drivers SQL Server")
    print("   [SOLUCION] Instala ODBC Driver 18 for SQL Server")
    print("              Ver: shared/database/README_ODBC_SETUP.md")

# 3. Driver recomendado
print()
print("3. Driver recomendado")
if "ODBC Driver 18 for SQL Server" in sql_drivers:
    recommended = "ODBC Driver 18 for SQL Server"
    print(f"   [OK] {recommended} (disponible)")
elif "ODBC Driver 17 for SQL Server" in sql_drivers:
    recommended = "ODBC Driver 17 for SQL Server"
    print(f"   [OK] {recommended} (disponible)")
elif sql_drivers:
    recommended = sql_drivers[0]
    print(f"   [ADVERTENCIA] Usando: {recommended}")
else:
    recommended = None
    print("   [ERROR] No hay drivers disponibles")

# 4. Ejemplo de connection string
print()
print("4. Ejemplo de connection string")
if recommended:
    print("   Para usar en tu codigo:")
    print()
    print(f'   driver = "{recommended}"')
    print('   server = "localhost,1433"  # o tu servidor')
    print('   database = "tu_base_datos"')
    print('   user = "tu_usuario"')
    print('   password = "tu_contraseña"')
    print()
    print("   connection_string = (")
    print(f'       f"DRIVER={{{{{driver}}}}};"')
    print('       f"SERVER={server};"')
    print('       f"DATABASE={database};"')
    print('       f"UID={user};"')
    print('       f"PWD={password};"')
    print('       f"TrustServerCertificate=yes;"')
    print('       f"Connection Timeout=15;"')
    print("   )")
else:
    print("   [ERROR] No se puede generar ejemplo sin driver")

# 5. Prueba de conexion (opcional)
print()
print("=" * 60)
print("PARA PROBAR LA CONEXION:")
print("=" * 60)
print()
print("Ejecuta el script de prueba con tus credenciales:")
print()
print('  python test_sql_connection.py "servidor,1433" "base_datos" "usuario" "contraseña"')
print()
print("Ejemplo:")
print('  python test_sql_connection.py "localhost,1433" "master" "sa" "TuPassword"')
print()
print("=" * 60)
