-- Esquema de Cassandra del proyecto Lichess Analytics (CONTRATO.md, sección 3).
-- Responsable: Integrante 2.
--
-- Ejecutar:  python -m carga_cassandra.crear_esquema
--   o bien:  docker exec -i lichess-cassandra cqlsh < carga_cassandra/esquema.cql
--
-- Cada tabla se diseña a partir de la consulta que la usa: toda consulta del dashboard
-- lee UNA sola partición (fecha, mes, apertura o jugador). Todo es IF NOT EXISTS, así que
-- se puede ejecutar las veces que se quiera.

CREATE KEYSPACE IF NOT EXISTS lichess
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- 1) Base: una fila por partida, particionada por día.
--    Consulta: SELECT * FROM partidas_por_fecha WHERE fecha = '2026-11-14';
CREATE TABLE IF NOT EXISTS lichess.partidas_por_fecha (
  fecha date,
  ritmo text,
  id_partida text,
  fecha_hora timestamp,
  jugador_blancas text,
  jugador_negras text,
  rating_blancas int,
  rating_negras int,
  ganador text,
  codigo_eco text,
  nombre_apertura text,
  cantidad_movimientos int,
  PRIMARY KEY ((fecha), ritmo, id_partida)
);

-- 2) Partidas de un día separadas por ritmo.
--    Consulta: SELECT * FROM partidas_por_dia WHERE fecha = '2026-11-14';
CREATE TABLE IF NOT EXISTS lichess.partidas_por_dia (
  fecha date,
  ritmo text,
  total int,
  victorias_blancas int,
  victorias_negras int,
  tablas int,
  PRIMARY KEY ((fecha), ritmo)
);

-- 3) Resumen de cada día, para la tendencia. Una partición por mes.
--    Consulta: SELECT * FROM resumen_diario WHERE anio_mes = '2026-11';
CREATE TABLE IF NOT EXISTS lichess.resumen_diario (
  anio_mes text,
  fecha date,
  total_partidas int,
  jugadores_activos int,
  victorias_blancas int,
  victorias_negras int,
  tablas int,
  promedio_movimientos double,
  PRIMARY KEY ((anio_mes), fecha)
) WITH CLUSTERING ORDER BY (fecha DESC);

-- 4) Historial de resultados de una apertura.
--    Consulta: SELECT * FROM resultados_por_apertura WHERE codigo_eco = 'B90';
CREATE TABLE IF NOT EXISTS lichess.resultados_por_apertura (
  codigo_eco text,
  fecha date,
  nombre_apertura text,
  total int,
  victorias_blancas int,
  victorias_negras int,
  tablas int,
  PRIMARY KEY ((codigo_eco), fecha)
) WITH CLUSTERING ORDER BY (fecha DESC);

-- 5) Actividad diaria de un jugador.
--    Consulta: SELECT * FROM actividad_por_jugador WHERE jugador = 'dr_tiger';
CREATE TABLE IF NOT EXISTS lichess.actividad_por_jugador (
  jugador text,
  fecha date,
  partidas int,
  victorias int,
  derrotas int,
  tablas int,
  rating_ultimo int,
  PRIMARY KEY ((jugador), fecha)
) WITH CLUSTERING ORDER BY (fecha DESC);

-- 6) KPIs calculados por el DAG (la crea Integrante 2, la llena Integrante 4).
--    Consulta: SELECT * FROM kpis_por_fecha WHERE fecha = '2026-11-14';
CREATE TABLE IF NOT EXISTS lichess.kpis_por_fecha (
  fecha date,
  kpi text,
  valor double,
  detalle text,
  calculado_en timestamp,
  PRIMARY KEY ((fecha), kpi)
);
