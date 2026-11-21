"""Genera una figura compacta a partir de los resultados de referencia."""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='amps_recencia_resultados.csv')
    p.add_argument('--output', default='docs/figures/comparacion.svg')
    args = p.parse_args()
    df = pd.read_csv(args.input)
    # Marcador y trazo distintos por serie: la figura no depende solo del color.
    models = {
        'CanEx calibrado (q=E[p^2])': ('CanEx calibrado', '#B45309', 's', '-'),
        'H3 actividad persistente (x entrenamiento)': ('H3', '#2563EB', 'o', '-'),
        'Independiente entre ediciones': ('Independencia', '#475569', '^', '--'),
        'Empírico (entrenamiento)': ('Empírico', '#15803D', 'D', ':'),
    }
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','svg.hashsalt':'mediaamps'})
    fig, axes = plt.subplots(1,2,figsize=(8.6,3.5),layout='constrained')
    for ax, field, title in zip(axes, ['err_abs_pp','sesgo_pp'], ['Error absoluto medio','Sesgo medio']):
        for key,(label,color,mk,ls) in models.items():
            y = df[df.modelo==key].groupby('ventana')[field].mean().reindex(['7d','14d','28d'])
            ax.plot(['7 días','14 días','28 días'], y, label=label, color=color, marker=mk, ls=ls, lw=2)
        ax.set_title(title,loc='left',fontweight='bold'); ax.set_ylabel('Puntos porcentuales'); ax.grid(axis='y',alpha=.2)
        ax.spines[['top','right']].set_visible(False)
        if field=='sesgo_pp': ax.axhline(0,color='#94A3B8',lw=.8)
    axes[0].legend(loc='upper left',frameon=False,fontsize=8)
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); fig.savefig(out,metadata={'Date':None}); plt.close(fig)
    if out.suffix == '.svg':  # título y descripción para lectores de pantalla
        t = out.read_text(encoding='utf-8')
        acc = ('<title>Comparación de modelos de cobertura por ventana temporal</title>'
               '<desc>Dos paneles con líneas para 7, 14 y 28 días. Izquierda: error absoluto medio '
               'en puntos porcentuales; derecha: sesgo medio. Series: CanEx calibrado, H3, '
               'independencia entre ediciones y referencia empírica. Los valores numéricos '
               'figuran en la tabla del README.</desc>')
        out.write_text(t.replace('version="1.1">', 'version="1.1" role="img">' + acc, 1), encoding='utf-8')

if __name__=='__main__': main()
