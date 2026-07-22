# Simulador de Transmisión Digital
### Compresión · Canal Ruidoso · Corrección de Errores · Codificación de Tunstall

> **Teoría de la Codificación — Universidad Nacional de Colombia · 2026**

| Autor | Correo |
|---|---|
| Juan Esteban Medina Cárdenas | juamedinaca@unal.edu.co |
| Sergio Andrés Hernández Salinas | serhernandezsa@unal.edu.co |

---

Este proyecto diseña e implementa un simulador integral de transmisión digital que recorre el ciclo completo de la comunicación digital: desde el análisis estadístico de la fuente hasta la recuperación confiable de la información en el receptor, pasando por compresión sin pérdida, transmisión sobre canal ruidoso y corrección de errores.

El simulador integra cuatro grandes áreas de la Teoría de la Información:

- **Análisis de fuente y entropía** (Shannon, 1948)
- **Codificación fuente** — Huffman, Shannon-Fano y Tunstall
- **Modelado de canal ruidoso** — Canal Binario Simétrico (BSC)
- **Codificación de canal** — Hamming(7,4)

---

## Objetivos

### General
Diseñar e implementar un simulador de transmisión digital que integre técnicas de compresión de información y corrección de errores para analizar la eficiencia y confiabilidad de la comunicación en canales ruidosos.

### Específicos
- Analizar distintas fuentes de información mediante el cálculo de probabilidades y entropía `H(X)`.
- Implementar algoritmos de codificación fuente: Huffman, Shannon-Fano y Tunstall.
- Construir el módulo analizador de Tunstall con diccionario configurable (parámetro `k`).
- Simular canales de comunicación ruidosos (BSC) variando la probabilidad de error `p`.
- Implementar códigos detectores y correctores: Hamming(7,4).
- Comparar experimentalmente eficiencia de compresión, capacidad del canal y tasa de recuperación.
- Visualizar resultados mediante tablas, gráficas y ejemplos completos de transmisión.

---

## Arquitectura del Sistema

El simulador sigue un **pipeline lineal de cinco módulos** con interfaces homogéneas, permitiendo intercambiar algoritmos con una sola línea de código.

```
 ┌──────────────┐    ┌──────────────────┐    ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
 │  M1  Fuente  │──> │  M2  Compresión  │───>│  M3  Canal  │───>│  M4  Corrección  │───>│ M5 Métricas│
 └──────────────┘    └──────────────────┘    └─────────────┘    └──────────────────┘    └─────────────┘
  Texto/imagen/bits   Huffman/Tunstall/SF      BSC  p config.     Hamming(7,4)           Dashboard
```

### M1 — Fuente de Información
- Soporta texto plano (UTF-8), imágenes PNG/JPG y secuencias de bits crudas.
- Calcula frecuencias y probabilidades `P(sᵢ)` de cada símbolo.
- Calcula entropía `H(X) = −Σ p·log₂p` en bits/símbolo.
- **Salida:** diccionario de probabilidades para los módulos siguientes.

### M2 — Codificación Fuente (Compresión)
- **Huffman:** construcción del árbol óptimo, longitud media `L̄ ≤ H(X) + 1`.
- **Shannon-Fano:** partición recursiva del alfabeto ordenado por probabilidad.
- **Tunstall ★:** expansión greedy del árbol hasta `2^k` hojas — longitud fija `k` bits.
- **Salida:** bitstring comprimido + tabla de códigos + métricas de eficiencia.

### M3 — Canal Ruidoso (BSC)
- Inversión de bit con probabilidad `p` configurable `(0 ≤ p ≤ 0.5)`.
- Cálculo de capacidad `C = 1 − H(p)` bits/uso.
- Generación reproducible con semilla aleatoria.
- **Salida:** secuencia recibida con errores + BER medido.

### M4 — Corrección de Errores
- **Hamming(7,4):** implementado desde cero con matrices generadora `G` y de paridad `H` — corrige 1 error, detecta 2 por bloque de 7 bits.
- Comparativa BER antes vs. después de decodificación.
- **Salida:** mensaje recuperado + síndrome + ganancia de codificación en dB.

> Reed-Solomon y un canal AWGN se consideraron en el diseño inicial pero quedaron fuera del alcance final del proyecto.

### M5 — Métricas y Visualización
- Tasa de compresión, BER, capacidad del canal, ganancia de codificación y eficiencia global del pipeline, consolidadas por `PipelineMetrics`.
- Dashboard Streamlit (`ui/app.py`): configuración por tarjetas (fuente / codificación / canal), resultados organizados en pestañas por módulo, y sliders interactivos para `p` y la semilla del canal.
- Histograma de frecuencias de símbolos.
- Exportación de métricas a CSV.

> La curva BER vs. `p` y la visualización del árbol de compresión (Huffman/Tunstall) están planeadas pero no implementadas aún.

---

### Métricas del Analizador

```python
H(X)       = −Σ p(s) · log₂ p(s)              # entropía de la fuente
L̄          = Σ |frase| · P(frase) / Σ P(frase) # longitud media de frase
Tasa       = k / L̄                             # bits por símbolo fuente
Eficiencia = (k / L̄) / H(X) × 100             # relativa al límite de Shannon
```


##  Estructura del Proyecto

```
codes-simulator/
├── source/                 # M1 — SourceReader + implementaciones
│   ├── source.py           # interfaz SourceReader, SourceStats
│   ├── text_reader.py
│   ├── image_reader.py
│   └── bits_reader.py
├── s_compression/           # M2 — SourceCodec + implementaciones
│   ├── base.py              # interfaz SourceCodec, Codebook, CompressionResult
│   ├── huffman.py
│   ├── shannon_fano.py
│   └── tunstall.py
├── channel/                 # M3 — Channel + implementaciones
│   ├── base.py               # interfaz Channel, TransmissionResult
│   └── bsc.py
├── coding/                   # M4 — ErrorCorrectingCode + implementaciones
│   ├── base.py                # interfaz ErrorCorrectingCode
│   └── hamming.py
├── metrics/                   # M5 — métricas consolidadas
│   ├── base.py                 # interfaces MetricsCollector / Visualizer
│   └── pipeline_metrics.py     # PipelineMetrics (registro + reporte + CSV)
├── core/
│   └── simulator.py            # Simulator: orquesta M1→M4
├── ui/
│   └── app.py                  # Dashboard Streamlit (M5)
├── .streamlit/
│   └── config.toml             # tema del dashboard
├── cli.py                      # CLI interactiva (InquirerPy)
├── gui.py                      # lanza `streamlit run ui/app.py`
├── main.py                     # punto de entrada (-m cli | -m gui)
└── pyproject.toml
```

No hay carpeta `tests/` — el proyecto no tiene una suite de pruebas configurada.

---

## Métricas Evaluadas

| Métrica | Definición | Unidad | Módulo |
|---|---|---|---|
| Entropía `H(X)` | `−Σ p·log₂p` | bits/símbolo | Todos |
| Longitud media `L̄` | `Σ len(frase)·P(frase)` | símbolos/frase | M2 |
| Eficiencia Tunstall | `k / L̄` relativa a `H(X)` | % | M2 — Tunstall |
| Tasa de error BER | bits erróneos / total | adim. | M3 |
| BER corregido | BER tras decodificador | adim. | M4 |
| Ganancia de codificación | `BER_antes / BER_después` | dB | M4 |
| Tasa de compresión | `\|original\| / \|comprimido\|` | adim. | M2 |
| Capacidad del canal `C` | `1 − H(p)` para BSC | bits/uso | M3 |

---

##  Herramientas y Dependencias

**Lenguaje principal:** Python 3.14

```
numpy        # matrices generadora (G) y de paridad (H) de Hamming(7,4)
Pillow       # lectura de imágenes PNG/JPG como fuente
InquirerPy   # prompts interactivos de la CLI
streamlit    # dashboard web interactivo (ui/app.py)
scipy        # reservada — sin uso actual en el código
seaborn      # reservada — sin uso actual en el código
matplotlib   # reservada — sin uso actual; el dashboard usa gráficas nativas de Streamlit
```

Instalar dependencias:
```bash
uv sync
```

Correr el simulador (CLI, modo por defecto):
```bash
uv run main.py
```

Correr el dashboard (Streamlit):
```bash
uv run main.py -m gui
```

---


## Referencias

- Shannon, C. E. (1948). *A Mathematical Theory of Communication.* Bell System Technical Journal.
- Huffman, D. A. (1952). *A Method for the Construction of Minimum-Redundancy Codes.* Proc. IRE.
- Tunstall, B. P. (1967). *Synthesis of Noiseless Compression Codes.* PhD Thesis, Georgia Tech.
- Cover, T. M., & Thomas, J. A. (2006). *Elements of Information Theory* (2nd ed.). Wiley.
- Lin, S., & Costello, D. J. (2004). *Error Control Coding* (2nd ed.). Pearson Prentice Hall.

---

*Simulador de Transmisión Digital · Teoría de la Codificación · UNAL · 2026*