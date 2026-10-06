# Mecha-Arena 🤖⚔️

> **Simulador de Ensamblaje y Combate Táctico de Mechas/Robots**
> Proyecto académico — Arquitectura en Capas + POO + Feature Branch Workflow

---

## 🚀 Instalación y Ejecución

```bash
# Clonar repositorio
git clone <URL_REPO>
cd mecha-arena

# (Opcional) Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS

# Ejecutar
python -m src.main
```

> Requiere **Python 3.10+** (se usa `match/case`). Sin dependencias externas.

---

## 🏗️ Arquitectura en Capas

```
src/
├── domain/         ← Capa 1: POO Pura (Célula 1)
│   ├── models.py       Componente, Mecha, Piloto, ResultadoCombate
│   └── exceptions.py   Jerarquía de excepciones personalizadas
├── services/       ← Capa 2: Lógica & Persistencia (Célula 2)
│   ├── data_manager.py Lectura/escritura JSON + catálogo
│   └── app_service.py  Motor de combate, torneos, casos de uso
└── ui/             ← Capa 3: Interfaz CLI (Célula 3)
    └── cli_interface.py Menú de consola con colores ANSI
```

---

## 🎮 Funcionalidades

| Módulo | Función |
|--------|---------|
| Pilotos | Registrar, listar, eliminar pilotos |
| Ensamblaje | Crear mecha, instalar/remover piezas del catálogo |
| Combate | Batalla 1v1 por turnos con logs detallados |
| Torneo | Round-Robin entre múltiples pilotos |
| Estadísticas | Clasificación y historial persistente en JSON |

---

## 🧩 Catálogo de Componentes

Cada pieza tiene **Tipo** (Cabeza, Torso, Brazos, Piernas, Arma) y **Rareza** con multiplicadores:

| Rareza | Multiplicador |
|--------|:---:|
| Común | x1.00 |
| Raro | x1.25 |
| Épico | x1.60 |
| Legendario | x2.00 |

---

## 🤝 Flujo de Trabajo Git (Feature Branch)

```
main ← solo el GitMaster hace merge
  └── feature/celula1-dominio
  └── feature/celula2-servicios
  └── feature/celula3-ui
```

**Regla:** NADIE hace commits directos en `main`.

---

## 🧪 Tests

```bash
python -m pytest tests/test_domain.py -v
```

---

## 📁 Prompt Base Utilizado (Co-pilotaje IA)

> *"Diseña un simulador de robots tácticos en Python con arquitectura en capas (domain/services/ui), POO pura con encapsulamiento, excepciones personalizadas, motor de combate por turnos con variación aleatoria, persistencia JSON y menú CLI con colores ANSI. Respeta la separación de capas y usa importaciones absolutas desde src/"*
