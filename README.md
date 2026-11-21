# mediaAMPS

**¿Cuántas personas ven al menos una vez un anuncio publicado en varios diarios? Este repositorio mide qué tan bien lo predicen distintos modelos, usando datos reales de lectura de prensa (AMPS 2011, Sudáfrica).**

[![Tests](https://github.com/majesus/mediaAMPS/actions/workflows/tests.yml/badge.svg)](https://github.com/majesus/mediaAMPS/actions/workflows/tests.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)

> **Alcance.** Investigación experimental, no un producto listo para planificar campañas. La referencia es la *última lectura que cada persona declara*, no un registro de anuncios realmente vistos. Los resultados no validan la distribución completa de contactos, solo la cobertura.

## Contenido

1. [Resumen en lenguaje llano](#1-resumen-en-lenguaje-llano)
2. [Inicio rápido](#2-inicio-rápido)
3. [Datos](#3-datos)
4. [Resultados](#4-resultados)
5. [Cómo funciona](#5-cómo-funciona)
6. [Reproducir y comprobar](#6-reproducir-y-comprobar)
7. [Estructura del repositorio](#7-estructura-del-repositorio)
8. [Limitaciones](#8-limitaciones)
9. [Glosario](#9-glosario)
10. [Recursos relacionados, licencia y citación](#10-recursos-relacionados-licencia-y-citación)

## 1. Resumen en lenguaje llano

**Problema.** Quien planifica medios necesita estimar la *cobertura*: el porcentaje de la población objetivo que ve el anuncio al menos una vez durante la campaña. Cuando se insertan anuncios en varios diarios durante semanas, esa cifra depende de cuánto se repiten los lectores entre diarios y entre días.

**Qué se hace aquí.** Con una encuesta real de 25.160 personas se comparan modelos que predicen esa cobertura. Cada modelo se entrena con una parte de las personas y se evalúa en otra parte distinta, frente a lo que esas personas dicen haber leído en los últimos 7, 14 o 28 días.

**Qué se encuentra.**

- Usar la frecuencia de lectura declarada tal cual (**CanEx** sin calibrar) produce errores de entre 5,5 y 8,5 puntos porcentuales, porque las personas sobrestiman cuánto leen.
- **Calibrar** las entradas reduce el error de forma drástica: es la mejora más importante del estudio.
- El modelo propuesto (**H3**) mejora a CanEx calibrado a 14 y 28 días, pero **no supera** a la simple frecuencia observada en los datos de entrenamiento (referencia empírica).
- La ventaja de H3 procede de la calibración y de las diferencias entre personas, no de modelar la persistencia temporal: sin ella el error es prácticamente el mismo.

**Para quién es útil.** Investigadores y docentes de medición de audiencias que deseen un banco de pruebas reproducible. No sustituye a un panel longitudinal.

## 2. Inicio rápido

Requisitos: Python 3.9 o posterior y unos dos minutos de cómputo.

```bash
git clone https://github.com/majesus/mediaAMPS.git
cd mediaAMPS
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v     # 10 pruebas, no necesitan los datos
```

Para reproducir los resultados hay que añadir antes los microdatos (sección [3](#3-datos)) y ejecutar:

```bash
python amps_recencia.py --data-dir data/amps --bootstrap 200
```

El programa imprime los errores y sesgos medios por modelo y ventana, y escribe `nueva_validacion.csv` y `nuevo_bootstrap.csv` sin sobrescribir los resultados incluidos.

## 3. Datos

Los microdatos **no se incluyen** en el repositorio (véase la nota de licencia en la sección 10).

| Característica | Detalle |
| :--- | :--- |
| Estudio | SAARF AMPS 2011, distribuido por DataFirst |
| Muestra | 25.160 personas |
| Soportes analizados | 22 diarios |
| Unidad de análisis | Persona × diario |
| Ponderación | Factor de elevación `pwgt` |
| Variables usadas | Lectura en los últimos seis meses, número habitual de ediciones leídas (de 5) y última lectura declarada |
| Ventanas de evaluación | 7, 14 y 28 días |

La cobertura de referencia de una combinación de diarios es la proporción ponderada de personas que declaran haber leído al menos uno de ellos dentro de la ventana.

**Cómo obtenerlos.** Se usa el extracto de la [consola docente mediaPlan](https://mareacultural.com/mediaPlan/). Descomprima los dos CSV, renómbrelos como indica la tabla y coloque los tres archivos en `data/amps/`.

| Archivo local | Fuente |
| :--- | :--- |
| `lectura.csv` | [CSV comprimido](https://mareacultural.com/mediaPlan/data/lectura_original_sin_recodificar.csv.gz) |
| `pesos.csv` | [CSV comprimido](https://mareacultural.com/mediaPlan/data/pesos_personas_qn_pwgt.csv.gz) |
| `catalog.js` | [Catálogo](https://mareacultural.com/mediaPlan/catalogo-amps.js) |

La [documentación de variables](https://mareacultural.com/mediaPlan/docs/muestra-datos.html) describe los códigos. Si falta algún archivo, el programa lo indica con un mensaje explícito.

## 4. Resultados

**Error absoluto medio de la cobertura**, en puntos porcentuales (pp): cuanto menor, mejor. Cada celda promedia 300 combinaciones de plan y partición.

| Modelo | 7 días | 14 días | 28 días |
| :--- | ---: | ---: | ---: |
| CanEx con frecuencia habitual | 5,55 | 6,69 | 8,50 |
| CanEx calibrado | 0,81 | 1,42 | 3,30 |
| Conteo fijo calibrado (tipo H2) | 1,54 | 1,37 | 1,07 |
| H3 con perfiles de entrenamiento | 0,93 | 1,01 | 1,01 |
| H3 sin persistencia (`phi_a` = 0) | 0,87 | 1,00 | 1,04 |
| Independencia entre ediciones | 0,76 | 0,79 | 0,82 |
| **Empírico (entrenamiento)** | **0,64** | **0,69** | **0,71** |

La variante de H3 que usa las covariables de las propias personas de validación obtiene 0,82, 0,71 y 0,50 pp. Se informa aparte porque dispone de información que los demás modelos no tienen.

**Lectura de la tabla.** CanEx calibrado reduce el error entre 4,7 y 6,9 veces a 7 y 14 días. H3 mejora a CanEx calibrado a 14 y 28 días, pero queda por detrás de la referencia empírica y de la independencia entre ediciones. Que `phi_a` = 0 rinda casi igual indica que la persistencia temporal no se puede identificar con estos datos.

![Dos paneles de líneas por ventana de 7, 14 y 28 días. Izquierda, error absoluto medio: CanEx calibrado crece de 0,8 a 3,3 pp; H3, la independencia y la referencia empírica permanecen entre 0,6 y 1,0 pp. Derecha, sesgo medio de las mismas cuatro series. Los valores exactos están en la tabla anterior y en el CSV de resultados.](docs/figures/comparacion.svg)

### Incertidumbre de las diferencias

Bootstrap pareado por persona (200 remuestras). Cada celda muestra la diferencia de error **H3 menos comparador** y su intervalo percentil del 95 %, en pp. Un valor negativo favorece a H3.

| Ventana | frente a CanEx calibrado | frente a empírico | frente a independencia |
| :--- | ---: | ---: | ---: |
| 7 días | +0,12 [−0,02; 0,24] | +0,29 [0,08; 0,43] | +0,17 [0,06; 0,24] |
| 14 días | −0,41 [−0,63; −0,08] | +0,32 [0,18; 0,40] | +0,23 [0,10; 0,29] |
| 28 días | −2,29 [−2,46; −1,68] | +0,31 [0,16; 0,39] | +0,19 [0,01; 0,26] |

Los intervalos son condicionales al entrenamiento y a los planes elegidos: no incluyen la incertidumbre de reestimar los modelos ni el diseño complejo de la encuesta. No prueban superioridad general. Detalle en [`bootstrap_resultados.csv`](bootstrap_resultados.csv).

## 5. Cómo funciona

1. Para cada categoría de frecuencia habitual se estima la probabilidad de leer en una semana y cuántas ediciones se leen cuando hay lectura.
2. Se calibran las propensiones individuales por diario con la lectura del último día.
3. Se ajustan dos parámetros latentes con momentos de recencia y duplicación: `phi_a` (persistencia semanal) y `rho_c` (dependencia entre diarios).
4. Se simulan secuencias de lectura con cinco ediciones semanales.
5. Se calcula la cobertura de cada combinación de diarios y se compara con la recencia declarada por personas reservadas para la evaluación.

El diseño usa 5 particiones, 60 planes de tres o cuatro diarios y 3 ventanas: **900 evaluaciones por modelo**. Comparten diarios y particiones, de modo que no son 900 observaciones independientes. Las ecuaciones completas están en la [especificación matemática](docs/metodologia.md).

## 6. Reproducir y comprobar

**Reproducción exacta.** El 21 de noviembre de 2026 se ejecutó la validación completa con Python 3.13, NumPy 2.5, pandas 3.0 y SciPy 1.18: las 7.200 filas de `amps_recencia_resultados.csv` y las 9 de `bootstrap_resultados.csv` coincidieron con diferencia máxima de 0,0. Las semillas están fijadas en el código.

**Versiones.** Las pruebas pasan con las versiones mínimas declaradas (NumPy 1.24, pandas 1.5, SciPy 1.10) en Python 3.11. La integración continua ejecuta Python 3.9, 3.11 y 3.13 en cada cambio.

Opciones habituales:

```bash
python amps_recencia.py --data-dir /ruta/a/amps --output mi_validacion.csv
python amps_recencia.py --data-dir data/amps --bootstrap 200 --bootstrap-output mi_bootstrap.csv
python -m pip install -r requirements-visualization.txt && python plot_results.py
```

**Pruebas.** Las 10 pruebas verifican la media ponderada, casos analíticos de CanEx (dos variables de Bernoulli, binomial independiente, truncamiento de celdas negativas), la reproducibilidad y el anidamiento de las simulaciones, la identidad del bootstrap, la carga de datos con un extracto sintético y la protección frente a enumeraciones de CanEx excesivas. En [`tests/check_canex_R.R`](tests/check_canex_R.R) hay casos para contrastar la traducción a Python con el paquete R; **esa comparación aún no se ha ejecutado**.

## 7. Estructura del repositorio

| Ruta | Función |
| :--- | :--- |
| [`amps_recencia.py`](amps_recencia.py) | Interfaz de línea de órdenes |
| [`mediaamps/data.py`](mediaamps/data.py) | Carga, validación y recodificación |
| [`mediaamps/models.py`](mediaamps/models.py) | Calibración, simulación H3 y CanEx |
| [`mediaamps/validation.py`](mediaamps/validation.py) | Experimento y bootstrap |
| [`plot_results.py`](plot_results.py) | Genera la figura accesible |
| [`tests/`](tests/) | Pruebas automáticas y casos para R |
| [`docs/metodologia.md`](docs/metodologia.md) | Especificación matemática |
| [`amps_recencia_resultados.csv`](amps_recencia_resultados.csv) | Resultados desagregados (7.200 filas) |
| [`bootstrap_resultados.csv`](bootstrap_resultados.csv) | Diferencias pareadas e intervalos |
| [`amps_recencia_salida.txt`](amps_recencia_salida.txt) | Salida de la ejecución original |

Columnas del CSV principal: `fold` (partición), `plan` (identificador de la combinación de diarios), `ventana`, `modelo`, `err_abs_pp` (error absoluto) y `sesgo_pp` (predicción menos referencia).

## 8. Limitaciones

- **Recencia, no seguimiento diario.** AMPS es transversal: los parámetros dinámicos se identifican de forma indirecta y dependen de los supuestos del modelo.
- **Cobertura, no frecuencia.** Solo se valida «al menos una lectura»; no se observa cuántos contactos se acumularon.
- **CanEx en Python.** Se usa una traducción propia de su formulación; no se afirma equivalencia numérica con el paquete R hasta contrastarla.
- **CanEx calibrado** (con `q = E[p²]`) es una construcción de este estudio, no un uso estándar del método.
- **Inferencia.** Los intervalos son condicionales; la superioridad general de H3 no está establecida.
- **Tamaño de los planes.** CanEx enumera todas las celdas posibles, por lo que el estudio se limita a planes de tres o cuatro diarios; el programa rechaza con un error explícito enumeraciones de más de cinco millones de celdas.

Continuación natural: validar en un panel longitudinal, separar los efectos de día y de diario y contrastar el valor añadido de cada componente.

## 9. Glosario

| Término | Significado |
| :--- | :--- |
| **AMPS** | All Media and Products Survey, encuesta sudafricana de consumo de medios |
| **Cobertura** (*reach*) | Porcentaje de personas expuestas al menos una vez |
| **Ventana** | Periodo de 7, 14 o 28 días en el que se mide la cobertura |
| **Frecuencia habitual** | Número de ediciones de cada cinco que la persona dice leer |
| **Recencia** | Cuándo leyó el diario por última vez, según su declaración |
| **Plan** | Combinación de tres o cuatro diarios con el mismo número de inserciones en cada uno |
| **Partición** (*fold*) | Quinta parte de las personas, reservada para evaluar un modelo entrenado con las demás |
| **pp** | Puntos porcentuales |
| **Error absoluto medio** | Promedio de la distancia entre cobertura predicha y observada |
| **Sesgo** | Predicción menos referencia; positivo significa sobrestimar |
| **CanEx** | Modelo de expansión canónica con marginales beta-binomiales |
| **H3** | Modelo de este repositorio: actividad semanal individual con persistencia y dependencia entre diarios |
| **Bootstrap pareado** | Remuestreo de personas que compara todos los modelos sobre las mismas remuestras |
| **`pwgt`** | Factor de elevación de la encuesta |

## 10. Recursos relacionados, licencia y citación

- [mediaPlanR](https://github.com/majesus/mediaPlanR): modelos clásicos de planificación de medios en R.
- [mediaPlan](https://mareacultural.com/mediaPlan/): aplicación docente de planificación y audiencias.

El código y la documentación se publican bajo licencia [MIT](LICENSE). Esa licencia **no se extiende a los microdatos de terceros**: consulte las condiciones de uso de AMPS y de DataFirst antes de redistribuirlos. Para citar el software, utilice [`CITATION.cff`](CITATION.cff) (GitHub ofrece la opción «Cite this repository»).
