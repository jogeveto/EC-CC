#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de despliegue para copiar módulos a Rocketbot.

Este script copia el módulo principal ExpedicionCopias y la carpeta shared
a la ruta de modules de Rocketbot configurada.
"""

import os
import shutil
import sys
import subprocess
import time
import platform
from pathlib import Path
from typing import List, Set, Optional

# Constante para crear nueva consola en Windows
if platform.system() == "Windows":
    CREATE_NEW_CONSOLE = 0x00000010
else:
    CREATE_NEW_CONSOLE = None

# ============================================================================
# CONFIGURACIÓN - MODIFICA ESTAS RUTAS SEGÚN TU INSTALACIÓN DE ROCKETBOT
# ============================================================================
ROCKETBOT_MODULES_PATH = r"C:\Users\kevin\Downloads\rocketbot_win_20250715\Rocketbot\modules"
# Ruta del ejecutable de Rocketbot (se calcula automáticamente si está vacío)
ROCKETBOT_EXECUTABLE_PATH = r"C:\Users\kevin\Downloads\rocketbot_win_20250715\Rocketbot\rocketbot.exe"
# Ejemplo manual: ROCKETBOT_EXECUTABLE_PATH = r"C:\Users\kevin\Downloads\rocketbot_win_20250715\Rocketbot\Rocketbot.exe"
# Ejemplo para Linux/Mac: 
#   ROCKETBOT_MODULES_PATH = "/opt/rocketbot/modules"
#   ROCKETBOT_EXECUTABLE_PATH = "/opt/rocketbot/rocketbot"
# ============================================================================

# Módulos a copiar
MODULES_TO_DEPLOY = [
    "ExpedicionCopias",
    "DynamicsCrmApi"
]

# Carpetas y archivos a excluir durante la copia
EXCLUDE_PATTERNS: Set[str] = {
    "__pycache__",
    ".git",
    ".gitignore",
    ".pytest_cache",
    ".mypy_cache",
    ".coverage",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".DS_Store",
    "Thumbs.db",
    "*.log",
    "*.tmp",
    "*.temp",
    ".vscode",
    ".idea",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "*.egg-info",
    "dist",
    "build",
    "screenshots",  # Excluir screenshots si no son necesarios
    "sessions",     # Excluir sesiones guardadas
}


def should_exclude(path: Path, root: Path) -> bool:
    """
    Determina si un archivo o carpeta debe ser excluido.
    
    Args:
        path: Ruta del archivo o carpeta a verificar
        root: Ruta raíz del proyecto
        
    Returns:
        True si debe ser excluido, False en caso contrario
    """
    # Obtener la ruta relativa desde la raíz
    try:
        rel_path = path.relative_to(root)
    except ValueError:
        return False
    
    # Verificar cada componente de la ruta
    for part in rel_path.parts:
        # Verificar patrones exactos
        if part in EXCLUDE_PATTERNS:
            return True
        
        # Verificar extensiones
        if part.endswith(('.pyc', '.pyo', '.pyd', '.log', '.tmp', '.temp')):
            return True
        
        # Verificar si comienza con punto y está en los patrones
        if part.startswith('.') and part[1:] in EXCLUDE_PATTERNS:
            return True
    
    return False


def find_rocketbot_processes() -> List[int]:
    """
    Encuentra los procesos de Rocketbot en ejecución.
    
    Returns:
        Lista de PIDs de procesos de Rocketbot
    """
    pids = []
    system = platform.system()
    
    try:
        if system == "Windows":
            # En Windows, buscar procesos que contengan "rocketbot" o "Rocketbot"
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False
            )
            
            for line in result.stdout.splitlines():
                if "rocketbot" in line.lower():
                    # Extraer PID (segundo campo en CSV)
                    parts = line.split(',')
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1].strip('"'))
                            pids.append(pid)
                        except (ValueError, IndexError):
                            continue
        else:
            # Linux/Mac: usar ps
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                check=False
            )
            
            for line in result.stdout.splitlines():
                if "rocketbot" in line.lower() and "grep" not in line.lower():
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            pids.append(pid)
                        except (ValueError, IndexError):
                            continue
    except Exception as e:
        print(f"⚠️  Advertencia al buscar procesos: {e}")
    
    return pids


def close_rocketbot() -> bool:
    """
    Cierra Rocketbot si está ejecutándose.
    
    Returns:
        True si se cerró exitosamente o no estaba ejecutándose, False en caso de error
    """
    print("\n" + "=" * 70)
    print("🛑 Cerrando Rocketbot...")
    print("=" * 70)
    
    pids = find_rocketbot_processes()
    
    if not pids:
        print("✅ Rocketbot no está ejecutándose")
        return True
    
    print(f"📋 Encontrados {len(pids)} proceso(s) de Rocketbot: {pids}")
    
    system = platform.system()
    all_closed = True
    
    for pid in pids:
        try:
            if system == "Windows":
                # Usar taskkill en Windows
                result = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    print(f"✅ Proceso {pid} cerrado exitosamente")
                else:
                    print(f"⚠️  No se pudo cerrar el proceso {pid}: {result.stderr}")
                    all_closed = False
            else:
                # Linux/Mac: usar kill
                result = subprocess.run(
                    ["kill", str(pid)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    print(f"✅ Proceso {pid} cerrado exitosamente")
                else:
                    print(f"⚠️  No se pudo cerrar el proceso {pid}: {result.stderr}")
                    all_closed = False
        except Exception as e:
            print(f"❌ Error al cerrar proceso {pid}: {e}")
            all_closed = False
    
    # Esperar un momento para que los procesos se cierren completamente
    if pids:
        print("⏳ Esperando que los procesos se cierren...")
        time.sleep(2)
        
        # Verificar que se cerraron
        remaining = find_rocketbot_processes()
        if remaining:
            print(f"⚠️  Advertencia: Aún quedan procesos ejecutándose: {remaining}")
            return False
    
    return all_closed


def get_rocketbot_executable_path(modules_path: Path) -> Optional[Path]:
    """
    Obtiene la ruta del ejecutable de Rocketbot.
    
    Args:
        modules_path: Ruta del directorio modules de Rocketbot
        
    Returns:
        Ruta del ejecutable o None si no se encuentra
    """
    # Si está configurado manualmente, usarlo
    if ROCKETBOT_EXECUTABLE_PATH:
        exe_path = Path(ROCKETBOT_EXECUTABLE_PATH)
        if exe_path.exists():
            return exe_path
        print(f"⚠️  La ruta configurada no existe: {ROCKETBOT_EXECUTABLE_PATH}")
    
    # Intentar encontrar el ejecutable automáticamente
    # Subir un nivel desde modules para llegar a la raíz de Rocketbot
    rocketbot_root = modules_path.parent
    
    # Posibles nombres de ejecutable
    possible_names = ["Rocketbot.exe", "rocketbot.exe", "Rocketbot", "rocketbot"]
    
    for name in possible_names:
        exe_path = rocketbot_root / name
        if exe_path.exists():
            return exe_path
    
    return None


def launch_rocketbot(executable_path: Path) -> bool:
    """
    Lanza Rocketbot.
    
    Args:
        executable_path: Ruta del ejecutable de Rocketbot
        
    Returns:
        True si se lanzó exitosamente, False en caso contrario
    """
    print("\n" + "=" * 70)
    print("🚀 Lanzando Rocketbot...")
    print("=" * 70)
    
    if not executable_path.exists():
        print(f"❌ ERROR: El ejecutable no existe: {executable_path}")
        return False
    
    try:
        # Cambiar al directorio del ejecutable para lanzarlo
        working_dir = executable_path.parent
        
        print(f"📂 Ejecutable: {executable_path}")
        print(f"📂 Directorio de trabajo: {working_dir}")
        
        # Lanzar Rocketbot con consola visible
        if platform.system() == "Windows":
            # En Windows, usar CREATE_NEW_CONSOLE para abrir una nueva ventana de consola
            subprocess.Popen(
                [str(executable_path)],
                cwd=str(working_dir),
                creationflags=CREATE_NEW_CONSOLE
            )
        else:
            # En Linux/Mac, lanzar normalmente (la consola ya está visible)
            subprocess.Popen(
                [str(executable_path)],
                cwd=str(working_dir)
            )
        
        print("✅ Rocketbot lanzado exitosamente con consola visible")
        time.sleep(1)  # Pequeña pausa para que inicie
        return True
        
    except Exception as e:
        print(f"❌ ERROR al lanzar Rocketbot: {e}")
        return False


def copy_directory(src: Path, dst: Path, root: Path) -> int:
    """
    Copia un directorio excluyendo archivos y carpetas no deseados.
    
    Args:
        src: Directorio origen
        dst: Directorio destino
        root: Ruta raíz del proyecto (para calcular rutas relativas)
        
    Returns:
        Número de archivos copiados
    """
    files_copied = 0
    
    # Crear directorio destino si no existe
    dst.mkdir(parents=True, exist_ok=True)
    
    # Recorrer todos los archivos y subdirectorios
    for item in src.iterdir():
        if should_exclude(item, root):
            print(f"  [EXCLUIDO] {item.name}")
            continue
        
        dst_item = dst / item.name
        
        if item.is_dir():
            # Recursivamente copiar subdirectorios
            files_copied += copy_directory(item, dst_item, root)
        elif item.is_file():
            # Copiar archivo
            try:
                shutil.copy2(item, dst_item)
                files_copied += 1
                print(f"  [COPIADO] {item.name}")
            except Exception as e:
                print(f"  [ERROR] No se pudo copiar {item.name}: {e}")
    
    return files_copied


def deploy_module(module_name: str, source_root: Path, target_modules_path: Path) -> bool:
    """
    Despliega un módulo a la ruta de Rocketbot.
    
    Args:
        module_name: Nombre del módulo a desplegar
        source_root: Ruta raíz del proyecto fuente
        target_modules_path: Ruta destino de modules de Rocketbot
        
    Returns:
        True si el despliegue fue exitoso, False en caso contrario
    """
    source_module = source_root / module_name
    target_module = target_modules_path / module_name
    
    if not source_module.exists():
        print(f"❌ ERROR: El módulo '{module_name}' no existe en {source_module}")
        return False
    
    if not source_module.is_dir():
        print(f"❌ ERROR: '{module_name}' no es un directorio")
        return False
    
    print(f"\n📦 Desplegando módulo: {module_name}")
    print(f"   Origen: {source_module}")
    print(f"   Destino: {target_module}")
    
    # Eliminar destino si existe
    if target_module.exists():
        print("   Eliminando versión anterior...")
        try:
            shutil.rmtree(target_module)
        except Exception as e:
            print(f"❌ ERROR: No se pudo eliminar el directorio destino: {e}")
            return False
    
    # Copiar módulo
    try:
        files_copied = copy_directory(source_module, target_module, source_root)
        print(f"✅ Módulo '{module_name}' desplegado exitosamente ({files_copied} archivos)")
        return True
    except Exception as e:
        print(f"❌ ERROR al desplegar '{module_name}': {e}")
        return False


def main():
    """Función principal del script de despliegue."""
    print("=" * 70)
    print("🚀 Script de Despliegue a Rocketbot")
    print("=" * 70)
    
    # Obtener ruta raíz del proyecto (donde está este script)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent
    
    # Validar ruta de Rocketbot
    rocketbot_modules = Path(ROCKETBOT_MODULES_PATH)
    
    if not rocketbot_modules.is_absolute():
        print("❌ ERROR: La ruta de Rocketbot debe ser absoluta")
        print(f"   Ruta configurada: {ROCKETBOT_MODULES_PATH}")
        sys.exit(1)
    
    # Obtener ruta del ejecutable de Rocketbot
    rocketbot_exe = get_rocketbot_executable_path(rocketbot_modules)
    
    # Cerrar Rocketbot si está ejecutándose
    if not close_rocketbot():
        print("\n⚠️  Advertencia: No se pudieron cerrar todos los procesos de Rocketbot")
        respuesta = input("¿Desea continuar con el despliegue de todas formas? (s/n): ")
        if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
            print("❌ Despliegue cancelado por el usuario")
            sys.exit(1)
    
    # Crear directorio modules si no existe
    if not rocketbot_modules.exists():
        print(f"\n📁 Creando directorio de modules: {rocketbot_modules}")
        try:
            rocketbot_modules.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"❌ ERROR: No se pudo crear el directorio: {e}")
            sys.exit(1)
    
    print(f"\n📂 Ruta del proyecto: {project_root}")
    print(f"📂 Ruta destino Rocketbot: {rocketbot_modules}")
    
    # Desplegar módulos
    print(f"\n{'=' * 70}")
    print("📦 Desplegando módulos...")
    print(f"{'=' * 70}")
    
    modules_success = []
    modules_failed = []
    
    for module in MODULES_TO_DEPLOY:
        if deploy_module(module, project_root, rocketbot_modules):
            modules_success.append(module)
        else:
            modules_failed.append(module)
    
    # Desplegar carpeta shared
    print(f"\n{'=' * 70}")
    print("📦 Desplegando carpeta shared...")
    print(f"{'=' * 70}")
    
    shared_source = project_root / "shared"
    shared_target = rocketbot_modules / "shared"
    
    if not shared_source.exists():
        print(f"❌ ERROR: La carpeta 'shared' no existe en {shared_source}")
        modules_failed.append("shared")
    else:
        print("\n📦 Desplegando: shared")
        print(f"   Origen: {shared_source}")
        print(f"   Destino: {shared_target}")
        
        if shared_target.exists():
            print("   Eliminando versión anterior...")
            try:
                shutil.rmtree(shared_target)
            except Exception as e:
                print(f"❌ ERROR: No se pudo eliminar el directorio destino: {e}")
                modules_failed.append("shared")
        
        if "shared" not in modules_failed:
            try:
                files_copied = copy_directory(shared_source, shared_target, project_root)
                print(f"✅ Carpeta 'shared' desplegada exitosamente ({files_copied} archivos)")
                modules_success.append("shared")
            except Exception as e:
                print(f"❌ ERROR al desplegar 'shared': {e}")
                modules_failed.append("shared")
    
    # Resumen final
    print(f"\n{'=' * 70}")
    print("📊 RESUMEN DEL DESPLIEGUE")
    print(f"{'=' * 70}")
    
    if modules_success:
        print(f"\n✅ Módulos desplegados exitosamente ({len(modules_success)}):")
        for module in modules_success:
            print(f"   - {module}")
    
    if modules_failed:
        print(f"\n❌ Módulos con errores ({len(modules_failed)}):")
        for module in modules_failed:
            print(f"   - {module}")
        sys.exit(1)
    else:
        print("\n🎉 ¡Despliegue completado exitosamente!")
        print(f"   Todos los módulos han sido copiados a: {rocketbot_modules}")
        
        # Lanzar Rocketbot si se encontró el ejecutable
        if rocketbot_exe:
            if not launch_rocketbot(rocketbot_exe):
                print("\n⚠️  Advertencia: No se pudo lanzar Rocketbot automáticamente")
                print(f"   Por favor, láncelo manualmente desde: {rocketbot_exe}")
        else:
            print("\n⚠️  No se encontró el ejecutable de Rocketbot")
            print("   Por favor, láncelo manualmente después del despliegue")


if __name__ == "__main__":
    main()

