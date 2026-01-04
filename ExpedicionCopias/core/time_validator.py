"""Validación de franjas horarias y días hábiles para Colombia."""
from datetime import datetime, time
from typing import List, Dict, Any, Callable
import functools
import holidays


class TimeValidator:
    """Validador de franjas horarias y días hábiles para Colombia."""

    def __init__(self, franjas_horarias: List[Dict[str, str]], pais: str = "CO") -> None:
        """
        Inicializa el validador con las franjas horarias y el país.

        Args:
            franjas_horarias: Lista de diccionarios con 'inicio' y 'fin' en formato HH:MM
            pais: Código del país para holidays (default: 'CO' para Colombia)
        """
        self.franjas_horarias = franjas_horarias
        self.holidays_colombia = holidays.Colombia()

    def es_dia_habil(self, fecha: datetime) -> bool:
        """
        Verifica si una fecha es un día hábil (no es festivo ni fin de semana).

        Args:
            fecha: Fecha a verificar

        Returns:
            True si es día hábil, False en caso contrario
        """
        if fecha.weekday() >= 5:
            return False
        
        return fecha.date() not in self.holidays_colombia

    def esta_en_franja_horaria(self, hora_actual: datetime, franjas: List[Dict[str, str]] | None = None) -> bool:
        """
        Verifica si la hora actual está dentro de alguna de las franjas horarias.

        Args:
            hora_actual: Hora actual a verificar
            franjas: Lista de franjas horarias (opcional, usa self.franjas_horarias si no se proporciona)

        Returns:
            True si está en alguna franja, False en caso contrario
        """
        if franjas is None:
            franjas = self.franjas_horarias
        
        if not franjas:
            return True
        
        hora_actual_time = hora_actual.time()
        
        for franja in franjas:
            inicio_str = franja.get("inicio", "")
            fin_str = franja.get("fin", "")
            
            try:
                inicio_time = datetime.strptime(inicio_str, "%H:%M").time()
                fin_time = datetime.strptime(fin_str, "%H:%M").time()
                
                if self._validar_franja(inicio_time, fin_time, hora_actual_time):
                    return True
            except (ValueError, KeyError):
                continue
        
        return False

    def _validar_franja(self, inicio_time: time, fin_time: time, hora_actual_time: time) -> bool:
        """
        Valida si la hora actual está dentro de una franja horaria.

        Args:
            inicio_time: Hora de inicio de la franja
            fin_time: Hora de fin de la franja
            hora_actual_time: Hora actual a validar

        Returns:
            True si está dentro de la franja, False en caso contrario
        """
        if inicio_time <= fin_time:
            return self._validar_franja_normal(inicio_time, fin_time, hora_actual_time)
        return self._validar_franja_cruzada(inicio_time, fin_time, hora_actual_time)

    def _validar_franja_normal(self, inicio_time: time, fin_time: time, hora_actual_time: time) -> bool:
        """
        Valida franja horaria que no cruza medianoche.

        Args:
            inicio_time: Hora de inicio de la franja
            fin_time: Hora de fin de la franja
            hora_actual_time: Hora actual a validar

        Returns:
            True si está dentro de la franja, False en caso contrario
        """
        return inicio_time <= hora_actual_time <= fin_time

    def _validar_franja_cruzada(self, inicio_time: time, fin_time: time, hora_actual_time: time) -> bool:
        """
        Valida franja horaria que cruza medianoche.

        Args:
            inicio_time: Hora de inicio de la franja
            fin_time: Hora de fin de la franja
            hora_actual_time: Hora actual a validar

        Returns:
            True si está dentro de la franja, False en caso contrario
        """
        return hora_actual_time >= inicio_time or hora_actual_time <= fin_time

    def debe_ejecutar(self, fecha_hora: datetime | None = None) -> bool:
        """
        Verifica si se debe ejecutar el proceso (día hábil y dentro de franja horaria).

        Args:
            fecha_hora: Fecha y hora a verificar (default: ahora)

        Returns:
            True si se debe ejecutar, False en caso contrario
        """
        if fecha_hora is None:
            fecha_hora = datetime.now()
        
        if not self.es_dia_habil(fecha_hora):
            return False
        
        return self.esta_en_franja_horaria(fecha_hora)


def verificar_franja_horaria(validator: TimeValidator) -> Callable:
    """
    Decorador para verificar franja horaria antes de ejecutar una función.

    Args:
        validator: Instancia de TimeValidator

    Returns:
        Decorador que verifica franja horaria antes de ejecutar
    """
    def decorador(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not validator.debe_ejecutar():
                raise ValueError(
                    "No se puede ejecutar: fuera de franja horaria o día no hábil"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorador
