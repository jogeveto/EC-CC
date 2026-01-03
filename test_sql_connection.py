#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para probar conexión a SQL Server"""

import sys
import pyodbc
from typing import Optional

def test_connection(server: str, database: str, user: str, password: str, driver: Optional[str] = None):
    """Prueba la conexión a SQL Server"""
    
    print("=" * 60)
    print("PRUEBA DE CONEXION A SQL SERVER")
    print("=" * 60)
    print()
    
    # Detectar driver si no se especifica
    if not driver:
        available_drivers = pyodbc.drivers()
        sql_drivers = [d for d in available_drivers if "SQL Server" in d]
        
        if "ODBC Driver 18 for SQL Server" in sql_drivers:
            driver = "ODBC Driver 18 for SQL Server"
            print(f"[INFO] Usando driver: {driver}")
        elif "ODBC Driver 17 for SQL Server" in sql_drivers:
            driver = "ODBC Driver 17 for SQL Server"
            print(f"[INFO] Usando driver: {driver}")
        elif sql_drivers:
            driver = sql_drivers[0]
            print(f"[INFO] Usando driver detectado: {driver}")
        else:
            print("[ERROR] No se encontraron drivers SQL Server")
            return False
    else:
        print(f"[INFO] Usando driver especificado: {driver}")
    
    # Construir connection string
    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=15;"
        f"Command Timeout=30;"
    )
    
    print()
    print("[INFO] Intentando conectar...")
    print(f"       Server: {server}")
    print(f"       Database: {database}")
    print(f"       User: {user}")
    print()
    
    try:
        # Intentar conexión
        conn = pyodbc.connect(connection_string, timeout=15)
        print("[OK] Conexion exitosa!")
        print()
        
        # Ejecutar consulta de prueba
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION AS Version, DB_NAME() AS CurrentDB, SYSTEM_USER AS CurrentUser")
        row = cursor.fetchone()
        
        print("[INFO] Informacion del servidor:")
        print(f"       Version: {row[0][:80]}...")
        print(f"       Base de datos actual: {row[1]}")
        print(f"       Usuario actual: {row[2]}")
        print()
        
        # Cerrar conexión
        cursor.close()
        conn.close()
        
        print("[OK] Prueba completada exitosamente")
        print("=" * 60)
        return True
        
    except pyodbc.Error as e:
        error_msg = str(e)
        print(f"[ERROR] Error de conexion: {error_msg}")
        print()
        
        # Mensajes de ayuda según el tipo de error
        if "IM002" in error_msg:
            print("[SOLUCION] El driver ODBC no se encuentra.")
            print("           Verifica que el driver este instalado:")
            print("           - ODBC Driver 18 for SQL Server")
            print("           - ODBC Driver 17 for SQL Server")
        elif "28000" in error_msg or "Login failed" in error_msg:
            print("[SOLUCION] Error de autenticacion.")
            print("           Verifica usuario y contraseña.")
        elif "08001" in error_msg or "11001" in error_msg or "Host desconocido" in error_msg:
            print("[SOLUCION] No se puede resolver el hostname.")
            print(f"           Verifica que el servidor '{server}' sea correcto y este accesible.")
        elif "timeout" in error_msg.lower():
            print("[SOLUCION] Timeout de conexion.")
            print("           Verifica que SQL Server este corriendo y accesible.")
            print("           Verifica que el firewall permita conexiones.")
        else:
            print("[INFO] Consulta la documentacion en:")
            print("       - shared/database/README_ODBC_SETUP.md")
            print("       - shared/database/ODBC_QUICK_REFERENCE.md")
        
        print("=" * 60)
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {str(e)}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    print()
    
    # Si se pasan argumentos, usarlos
    if len(sys.argv) >= 5:
        server = sys.argv[1]
        database = sys.argv[2]
        user = sys.argv[3]
        password = sys.argv[4]
        driver = sys.argv[5] if len(sys.argv) > 5 else None
    else:
        # Mostrar instrucciones
        print("USO DEL SCRIPT:")
        print("=" * 60)
        print("python test_sql_connection.py <server> <database> <user> <password> [driver]")
        print()
        print("Ejemplos:")
        print('  python test_sql_connection.py "localhost,1433" "master" "sa" "TuPassword"')
        print('  python test_sql_connection.py "servidor.dominio.com" "RPA_Automatizacion" "usuario" "password" "ODBC Driver 18 for SQL Server"')
        print()
        print("O puedes ejecutarlo sin argumentos para modo interactivo:")
        print("  python test_sql_connection.py")
        print()
        print("=" * 60)
        print()
        
        # Intentar modo interactivo solo si hay stdin disponible
        try:
            server = input("Server (ej: localhost,1433): ").strip()
            if not server:
                print("[INFO] Usando valores de prueba (pueden fallar)")
                server = "localhost,1433"
                database = "master"
                user = "sa"
                password = "test"
            else:
                database = input("Database (ej: master): ").strip() or "master"
                user = input("User (ej: sa): ").strip() or "sa"
                password = input("Password: ").strip()
                if not password:
                    print("[ERROR] La contraseña es requerida")
                    sys.exit(1)
            
            driver_input = input("Driver (Enter para auto-detectar): ").strip()
            driver = driver_input if driver_input else None
        except (EOFError, KeyboardInterrupt):
            print()
            print("[INFO] Modo interactivo no disponible. Usa argumentos de línea de comandos.")
            print("       Ejemplo: python test_sql_connection.py localhost,1433 master sa password")
            sys.exit(1)
    
    print()
    success = test_connection(server, database, user, password, driver)
    sys.exit(0 if success else 1)
