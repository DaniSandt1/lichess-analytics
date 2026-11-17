
/*
Consulta 1: Jugador con más rivales distintos
Cuenta cuántos jugadores diferentes enfrentó cada jugador.
*/

MATCH (j:Jugador)-[:ENFRENTO]-(rival:Jugador)
RETURN
    j.id AS jugador,
    j.nombre AS nombre,
    COUNT(DISTINCT rival) AS rivales_distintos
ORDER BY rivales_distintos DESC
LIMIT 5;


/*
Consulta 2: Apertura que conecta a más jugadores
Cuenta jugadores únicos que utilizaron cada apertura,
ya sea jugando con blancas o con negras.
*/

MATCH (a:Apertura)<-[:USA_APERTURA]-(p:Partida)
MATCH (j:Jugador)-[:JUEGA_BLANCAS|JUEGA_NEGRAS]->(p)
RETURN
    a.codigo_eco AS codigo_eco,
    a.nombre AS apertura,
    COUNT(DISTINCT j) AS jugadores_distintos
ORDER BY jugadores_distintos DESC
LIMIT 1;


/*
Consulta 3: Subgrafo de un jugador y sus rivales
Muestra visualmente sus conexiones de enfrentamiento.
*/

MATCH (j:Jugador {id: 'affa19'})
      -[r:ENFRENTO]-(rival:Jugador)
RETURN j, r, rival
ORDER BY r.veces DESC LIMIT 60;