# mediaAMPS

**Estimación y validación de cobertura publicitaria con microdatos AMPS 2011.**

Este repositorio estudia cómo se acumula la audiencia de varios diarios a lo largo de distintas ventanas temporales, y compara un modelo individualizado de actividad semanal persistente (H3) con CanEx y otros procedimientos de referencia.

> **Alcance:** investigación experimental. La referencia es la última lectura declarada por la persona entrevistada, no un registro longitudinal de anuncios efectivamente vistos. Los resultados no constituyen una validación de la distribución completa de contactos.

## 1. Datos

| Característica | Detalle |
| :--- | :--- |
| Estudio | SAARF AMPS 2011 (DataFirst) |
| Muestra | 25.160 personas |
| Soportes analizados | 22 diarios |
| Unidad de análisis | Persona × soporte |
| Ponderación | Factor `pwgt` |
| Ventanas | 7, 14 y 28 días |

Se utilizan la frecuencia habitual y la última lectura declarada. La cobertura de referencia de una combinación de diarios es la proporción ponderada que declara haber leído al menos uno dentro de la ventana.

## 2. Resultados de referencia

**Error absoluto medio de cobertura**, en puntos porcentuales (menor es mejor). Los resultados proceden del archivo de salida incluido, con 300 combinaciones plan–partición por ventana y modelo.

| Modelo | 7 días | 14 días | 28 días |
| :--- | ---: | ---: | ---: |
| CanEx — frecuencia habitual | 5,55 | 6,69 | 8,50 |
| CanEx — calibrado | 0,81 | 1,42 | 3,30 |
| Conteo fijo (tipo H2) | 1,54 | 1,37 | 1,07 |
| H3 — perfiles de entrenamiento | 0,93 | 1,01 | 1,01 |
| H3 sin persistencia | 0,87 | 1,00 | 1,04 |
| Independencia entre ediciones | 0,76 | 0,79 | 0,82 |
| **Empírico (entrenamiento)** | **0,64** | **0,69** | **0,71** |

La variante H3 que utiliza covariables de las personas de validación obtiene 0,82, 0,71 y 0,50 pp, respectivamente. Se informa por separado porque dispone de información diferente a los modelos que predicen únicamente desde entrenamiento.

**Interpretación:** calibrar las entradas de CanEx reduce considerablemente el error. H3 con perfiles de entrenamiento mejora sobre CanEx calibrado en 14 y 28 días, pero no supera sistemáticamente la referencia empírica ni la independencia entre ediciones. La contribución de la persistencia requiere validación adicional.

## 3. Cómo funciona

1. Se estima, para cada categoría de frecuencia habitual, la probabilidad de actividad semanal y el número esperado de lecturas cuando existe actividad.
2. Se calibran las propensiones individuales por soporte a partir de la lectura del último período.
3. Se ajustan dos parámetros latentes mediante momentos de recencia y duplicación: `phi_a` (persistencia semanal) y `rho_c` (dependencia entre soportes).
4. Se simulan secuencias de lectura bajo el supuesto de cinco ediciones semanales.
5. Se estima la cobertura de cada combinación de diarios y se compara con la recencia declarada en una partición de personas reservada.

Se emplean cinco particiones, 60 combinaciones de tres o cuatro diarios y tres ventanas: **900 evaluaciones por modelo**. Las evaluaciones comparten soportes y particiones, por lo que no son 900 observaciones independientes a efectos inferenciales.

## 4. Descargar los datos

Los microdatos no se incluyen en el repositorio. Pueden obtenerse del extracto utilizado en la [consola docente mediaPlan](https://mareacultural.com/mediaPlan/).

| Archivo local | Fuente |
| :--- | :--- |
| `lectura.csv` | [Descargar CSV comprimido](https://mareacultural.com/mediaPlan/data/lectura_original_sin_recodificar.csv.gz) |
| `pesos.csv` | [Descargar CSV comprimido](https://mareacultural.com/mediaPlan/data/pesos_personas_qn_pwgt.csv.gz) |
| `catalog.js` | [Descargar catálogo](https://mareacultural.com/mediaPlan/catalogo-amps.js) |

Descomprime los dos CSV, renómbralos como se indica y coloca los tres archivos en `data/amps/`. Consulta la [documentación de variables](https://mareacultural.com/mediaPlan/docs/muestra-datos.html) para conocer sus códigos. Revisa las condiciones de uso de la fuente antes de redistribuir los microdatos.

## 5. Reproducir el análisis

Requiere Python 3.9 o posterior, NumPy, pandas y SciPy.

```bash
git clone https://github.com/majesus/mediaAMPS.git
cd mediaAMPS
python -m pip install -r requirements.txt
python amps_recencia.py --data-dir data/amps
```

Para utilizar otra carpeta o evitar sobrescribir los resultados de referencia:

```bash
python amps_recencia.py --data-dir /ruta/a/amps --output nueva_validacion.csv
```

El programa imprime los errores y sesgos medios y genera un CSV con los resultados individuales por partición, planificación, ventana y modelo. Utiliza semillas fijadas en el código para facilitar la reproducción.

## 6. Archivos del repositorio

| Archivo | Función |
| :--- | :--- |
| [`amps_recencia.py`](amps_recencia.py) | Calibración, simulación, CanEx y validación |
| [`amps_recencia_resultados.csv`](amps_recencia_resultados.csv) | Resultados desagregados (7.200 filas) |
| [`amps_recencia_salida.txt`](amps_recencia_salida.txt) | Resumen de la ejecución original |
| [`requirements.txt`](requirements.txt) | Dependencias de Python |

El CSV contiene `fold` (partición), `plan` (identificador de planificación), `ventana`, `modelo`, `err_abs_pp` (error absoluto en pp) y `sesgo_pp` (predicción menos referencia, en pp).

## 7. Limitaciones y líneas de investigación

- **Recencia, no seguimiento diario:** AMPS es transversal; los parámetros dinámicos se identifican indirectamente mediante momentos de recencia, sujetos a los supuestos del modelo.
- **Cobertura, no frecuencia completa:** la validación compara eventos de al menos una lectura; no permite observar cuántos contactos se acumularon realmente.
- **Comparación:** CanEx se ejecuta con una traducción Python de su formulación; no se afirma equivalencia numérica con el paquete R sin una comprobación independiente.
- **Incertidumbre:** no se presentan intervalos de confianza ni contrastes pareados en esta ejecución. La superioridad predictiva general de H3 no está establecida.

La continuación natural es validar en un panel longitudinal, controlar los efectos de día y soporte, preservar las marginales y contrastar el valor añadido de cada componente frente a referencias empíricas y probabilísticas.

## Recursos relacionados

- [mediaPlanR](https://github.com/majesus/mediaPlanR): modelos clásicos de planificación de medios.
- [mediaPlan](https://mareacultural.com/mediaPlan/): aplicación docente de planificación y análisis de audiencias.
