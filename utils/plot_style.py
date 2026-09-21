"""Padrões visuais compartilhados do painel (fonte + paleta azul→roxo)."""

# Tipografia
FONT_FAMILY = "Inter Tight, sans-serif"

# Paleta principal — gradiente azul → roxo
ACCENT = "#58a6ff"        # azul (primário)
BLUE_VIOLET = "#6f7cf6"   # azul-violeta
VIOLET = "#8a63e8"        # violeta médio
PURPLE = "#8957e5"        # roxo
PURPLE_DEEP = "#a855f7"   # roxo intenso (destaque / severidade)

GRADIENT_UV = [ACCENT, BLUE_VIOLET, VIOLET, PURPLE, PURPLE_DEEP]

# Escala para heatmaps (risco/severidade crescente)
HEAT_GRADIENT = [[0.0, ACCENT], [0.5, BLUE_VIOLET], [1.0, PURPLE_DEEP]]

# Cores por turno — acompanham o ciclo do dia (madrugada = roxo mais escuro)
TURNO_COLORS = {
    "Madrugada": "#6d28d9",
    "Manhã": ACCENT,
    "Tarde": BLUE_VIOLET,
    "Noite": PURPLE,
}

HOVERLABEL = dict(
    bgcolor="rgba(22,27,34,0.95)",
    bordercolor=ACCENT,
    font=dict(family=FONT_FAMILY, size=13, color="#e6edf3"),
)


def apply_hover(fig, hovermode="closest", spike_axis=None):
    """Aplica hoverlabel padronizado e, se pedido, linha sutil de destaque.

    fig : plotly.graph_objects.Figure
    hovermode : str — "closest" para barras/pizza, "x unified" para séries.
    spike_axis : None | str | iterable — "x", "y" ou ambos.
    """
    layout = {"hoverlabel": HOVERLABEL, "hovermode": hovermode}

    if spike_axis is not None:
        if isinstance(spike_axis, str):
            spike_axis = [spike_axis]
        spike = dict(
            showspikes=True,
            spikemode="across",
            spikethickness=1,
            spikecolor="rgba(88,166,255,.5)",
            spikedash="solid",
        )
        if "x" in spike_axis:
            layout["xaxis"] = spike
        if "y" in spike_axis:
            layout["yaxis"] = spike

    fig.update_layout(**layout)
    return fig