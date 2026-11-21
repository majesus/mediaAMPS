# Metodología y especificación

## Estimando y referencia

AMPS 2011 mide hábitos y recencia declarada, no trayectorias de exposición. Para una planificación de diarios $S$ y ventana $h$ (7, 14 o 28 días), sea $Y_{ijh}$ el indicador de lectura del soporte $j$ en la ventana. Se emplean los códigos de recencia ≤7, ≤8 y ≤9, respectivamente. La referencia en una muestra $T$ es

$$C_h(S;T)=\frac{\sum_{i\in T}w_i\mathbf{1}\{\max_{j\in S}Y_{ijh}=1\}}{\sum_{i\in T}w_i}.$$

El supuesto de cinco ediciones por semana traduce ventanas en 5, 10 y 20 inserciones por diario, respectivamente. No equivale a validar un calendario publicitario concreto ni la distribución de contactos completos. La muestra y definición de recencia pueden contener error de medición.

## H3: actividad semanal persistente

Sea $x_{ij}\in\{0,\dots,5\}$ la frecuencia habitual, con -1 para no lector/frecuencia ausente según la recodificación de referencia. En entrenamiento, se estima de forma agrupada por categoría $x$ la tasa semanal $a_x=\Pr(Y_{ij,7}=1\mid x)$ y $\mu_x=7\Pr(Y_{ij,ayer}=1\mid x)$. Se define

$$c_x=\operatorname{clip}(\mu_x/a_x,1,5),\qquad a_{ij}=\operatorname{clip}(s_j a_{x_{ij}},0,1).$$

$s_j$ es una corrección de escala por soporte calculada como cociente de audiencia ayer observada y predicha antes del truncamiento. No garantiza ajuste exacto una vez aplicado el truncamiento. Para $x=-1$ se asigna $a_{ij}=0$.

Para cada semana $b$, un proceso gaussiano estacionario combina un factor común y otro específico:

$$\epsilon_{ijb}=\sqrt{\rho_c}G_{ib}+\sqrt{1-\rho_c}E_{ijb},\quad Z_{ijb}=\phi_a Z_{ij,b-1}+\sqrt{1-\phi_a^2}\epsilon_{ijb}.$$

$G,E$ son normales estándar independientes. El estado activo es $A_{ijb}=\mathbf{1}\{Z_{ijb}<\Phi^{-1}(a_{ij})\}$. Numéricamente se acotan los umbrales extremos. En semana activa, el número de ediciones leídas se obtiene redondeando estocásticamente $c_x$: $K=\lfloor c_x\rfloor+\mathrm{Bernoulli}(c_x-\lfloor c_x\rfloor)$. Se eligen $K$ ediciones uniformemente sin reemplazo entre cinco. En otra semana, $K=0$.

La población se integra mediante factores de elevación y simulaciones independientes de las respuestas reservadas. En la versión de entrenamiento, también se reservan los perfiles de evaluación. El modelo con perfiles de validación se etiqueta aparte.

### Calibración dinámica

Se elige $\phi_a\in\{0,.2,.4,.6,.8,.9\}$ minimizando el error cuadrático relativo de la suma de audiencias de 14 y 28 días, con $\rho_c=.2$. A continuación se selecciona $\rho_c\in\{0,.1,\ldots,.6\}$ minimizando la discrepancia en la suma ponderada de duplicaciones de ayer. Es un ajuste por momentos simulados, no una identificación longitudinal directa ni una optimización conjunta.

## CanEx y comparadores

CanEx aproxima la distribución conjunta de contactos mediante una expansión canónica de primer orden. Para cada soporte $j$ con audiencia por inserción $p_j$, duplicación interna $q_j$, número de inserciones $n_j$ y duplicación entre soportes $d_{jk}$, se emplea una marginal beta-binomial. El parámetro de correlación intraclase es

$$r_j=\frac{q_j-p_j^2}{p_j(1-p_j)},\qquad \alpha_j=p_j(1/r_j-1),\quad \beta_j=(1-p_j)(1/r_j-1).$$

Se usan los límites binomial ($r=0$) y polarizado ($r=1$). Para $n_j=1$ se usa Bernoulli. Sea $f_j$ la marginal, $z_j(k_j)$ su valor estandarizado y $R_{jk}=(d_{jk}-p_jp_k)/\sqrt{p_j(1-p_j)p_k(1-p_k)}$. Entonces

$$g(\mathbf k)=\prod_j f_j(k_j)\left[1+\sum_{j<k}R_{jk}z_j(k_j)z_k(k_k)\right].$$

Las celdas negativas se truncan a cero y se renormaliza. La cobertura es $1-g^+(\mathbf0)/\sum_{\mathbf k}g^+(\mathbf k)$. La corrección puede alterar las marginales y la media de contactos: la opción `full=True` devuelve el diagnóstico de masa negativa y media esperada/obtenida. Se rechazan matrices no semidefinidas positivas y parámetros internos inadmisibles. Es una traducción de la formulación de [mediaPlanR](https://github.com/majesus/mediaPlanR), no una afirmación de equivalencia de toda su interfaz.

Entradas benchmark: $p=E_w[x/5]$, $q=E_w[x(x-1)/20]$ y $d_{jk}=E_w[p_{ij}p_{ik}]$. Entradas calibradas: $p_{ij}=a_{ij}c_{ij}/5$, $p_j=E_w[p_{ij}]$, $q_j=E_w[p_{ij}^2]$, $d_{jk}=E_w[p_{ij}p_{ik}]$. El segundo comparador comparte las propensiones de H3, de modo que la ventaja no se confunde únicamente con su calibración. 

Independencia entre ediciones: $C=E_w[1-\prod_j(1-p_{ij})^{n_j}]$. El modelo empírico es $C_h(S;T_{train})$. El conteo fijo y la ablación $\phi_a=0$ mantienen los otros parámetros del ajuste completo (no se reestiman).

## Validación e incertidumbre

Cinco particiones de personas, 60 combinaciones aleatorias de tres o cuatro diarios, tres ventanas. La estimación se realiza en entrenamiento; la cobertura de referencia se mide en la partición de prueba. MAE y sesgo se reportan en puntos porcentuales, agregando planes y particiones. Los planes y entrenamientos parcialmente solapados no son repeticiones independientes.

El bootstrap opcional toma, en cada partición, 200 remuestras de personas con reemplazo y conserva el mismo vector de multiplicidades para todos los planes. La cobertura se recalcula ponderando por `pwgt` y se calcula la diferencia de MAE H3 menos comparador; se combinan los cinco pliegues y se usan cuantiles percentiles. **Los intervalos son condicionales a los modelos ya ajustados, planes, particiones y simulaciones**; no reestiman parámetros ni reflejan diseño complejo de encuesta. No son contrastes confirmatorios de superioridad universal ni ajustan multiplicidad.

## Reproducibilidad

La refactorización conserva las semillas del experimento inicial. Sobre el extracto de referencia, las 7.200 filas y errores/sesgos reproducidos coinciden con los archivos originales (diferencia numérica máxima 0 en la ejecución comprobada). El bootstrap usa una semilla separada, de modo que no modifica las simulaciones del benchmark.

R no se ejecutó en esta validación. La prueba `tests/check_canex_R.R` contiene fixtures para cotejar `mediaPlanR` en un entorno R; las pruebas Python comprueban propiedades matemáticas, no paridad de runtime. La estimación de exposición longitudinal y la validación de frecuencia completa requieren un panel real.
