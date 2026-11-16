"""Cálculo automático de los KPIs (última tarea del DAG).

Responsable: Integrante 4.
Estado: PLANTILLA.

Qué tiene que hacer (CONTRATO.md, sección 6):
- Calcular los 6 KPIs para `fecha` leyendo de Cassandra (y de Neo4j para el KPI 4).
- Escribir cada uno en la tabla kpis_por_fecha de Cassandra (una fila por KPI).
- Devolver un dict {nombre_kpi: valor} (sale en el log de Airflow).
"""


def calcular_kpis(fecha: str) -> dict:
    """FUNCIÓN DEL CONTRATO. `fecha` es "YYYY-MM-DD" (la fecha lógica del DAG)."""
    print(f"[PENDIENTE - Integrante 4] calcular_kpis({fecha})")
    return {}
