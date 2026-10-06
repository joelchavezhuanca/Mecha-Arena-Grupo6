"""
CAPA 1 - DOMINIO POO
Célula 1: Excepciones personalizadas de Mecha-Arena.

Jerarquía:
    MechaArenaError (base)
    ├── ComponenteNoValidoError
    ├── PuntosDeVidaInvalidosError
    ├── NombreInvalidoError
    ├── MechaIncompleroError
    ├── PilotoNoEncontradoError
    └── CombateInvalidoError
"""


class MechaArenaError(Exception):
    """Excepción base de la aplicación Mecha-Arena."""
    def __init__(self, mensaje: str = "Error en Mecha-Arena.") -> None:
        self.mensaje = mensaje
        super().__init__(self.mensaje)

    def __str__(self) -> str:
        return f"[MechaArena] {self.mensaje}"


class ComponenteNoValidoError(MechaArenaError):
    """Se lanza cuando se intenta instalar un componente inválido o duplicado."""
    def __init__(self, mensaje: str = "Componente no válido.") -> None:
        super().__init__(mensaje)


class PuntosDeVidaInvalidosError(MechaArenaError):
    """Se lanza cuando los puntos de vida resultan en un estado inconsistente."""
    def __init__(self, mensaje: str = "Puntos de vida inválidos.") -> None:
        super().__init__(mensaje)


class NombreInvalidoError(MechaArenaError):
    """Se lanza cuando un nombre está vacío o contiene caracteres no permitidos."""
    def __init__(self, mensaje: str = "Nombre inválido.") -> None:
        super().__init__(mensaje)


class MechaIncompleroError(MechaArenaError):
    """Se lanza cuando un Mecha no tiene los componentes mínimos para combatir."""
    def __init__(self, mensaje: str = "El Mecha no está completo para el combate.") -> None:
        super().__init__(mensaje)


class PilotoNoEncontradoError(MechaArenaError):
    """Se lanza cuando se busca un piloto que no existe en el registro."""
    def __init__(self, nombre: str = "") -> None:
        msg = f"Piloto '{nombre}' no encontrado." if nombre else "Piloto no encontrado."
        super().__init__(msg)


class CombateInvalidoError(MechaArenaError):
    """Se lanza cuando se intenta iniciar un combate con condiciones inválidas."""
    def __init__(self, mensaje: str = "Combate inválido.") -> None:
        super().__init__(mensaje)


class ArchivoCorruptoError(MechaArenaError):
    """Se lanza cuando el archivo de datos está dañado o mal formado."""
    def __init__(self, ruta: str = "") -> None:
        msg = f"El archivo '{ruta}' está corrupto o mal formado." if ruta else "Archivo corrupto."
        super().__init__(msg)
