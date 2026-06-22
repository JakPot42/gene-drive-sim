"""
Matplotlib visualization for the gene drive simulation.
All pyplot imports are lazy so the backend can be configured by cli.py before import.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulation import Simulation, SimulationResult

_COLORS = {
    "normal": "#4CAF50",
    "gene_drive": "#FF5722",
    "sterile": "#9E9E9E",
    "resistant": "#9C27B0",
    "frogs": "#1565C0",
    "drive_line": "#F57F17",
    "resist_line": "#6A1B9A",
}


class LiveVisualizer:
    """Updates a matplotlib figure in real time while the simulation runs."""

    def __init__(self, title: str = "Gene Drive Ecosystem Simulation") -> None:
        import matplotlib.pyplot as plt

        self._plt = plt
        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(12, 5))
        self.ax.set_title(title, fontsize=12)
        self.ax.set_xlabel("Tick")
        self.ax.set_ylabel("Population")
        self.fig.tight_layout()

    def update(self, sim: "Simulation") -> None:
        if not sim.history:
            return

        h = sim.history
        ticks = [s.tick for s in h]

        self.ax.clear()
        self.ax.stackplot(
            ticks,
            [s.normal for s in h],
            [s.gene_drive for s in h],
            [s.sterile for s in h],
            [s.resistant for s in h],
            labels=["Normal", "Gene Drive", "Sterile", "Resistant"],
            colors=[_COLORS["normal"], _COLORS["gene_drive"],
                    _COLORS["sterile"], _COLORS["resistant"]],
            alpha=0.75,
        )
        self.ax.plot(ticks, [s.frogs for s in h], "-",
                     color=_COLORS["frogs"], linewidth=2.5, label="Frogs", zorder=5)

        if sim.gene_drive_released:
            self.ax.axvline(sim.gene_drive_release_tick,
                            color=_COLORS["drive_line"], linestyle="--",
                            linewidth=1.5, alpha=0.9, label="Drive Release")

        if sim.resistance_tick is not None:
            self.ax.axvline(sim.resistance_tick,
                            color=_COLORS["resist_line"], linestyle=":",
                            linewidth=1.5, alpha=0.9, label="Resistance Emerges")

        self.ax.legend(loc="upper right", fontsize=8)
        self.ax.set_title("Gene Drive Ecosystem Simulation", fontsize=12)
        self.ax.set_xlabel("Tick")
        self.ax.set_ylabel("Population")
        self.fig.tight_layout()
        self._plt.draw()
        self._plt.pause(0.001)

    def keep_open(self) -> None:
        self._plt.ioff()
        self._plt.show()

    def close(self) -> None:
        self._plt.close(self.fig)


def save_summary_plot(result: "SimulationResult", output_path: str) -> None:
    """Save a final annotated summary plot to disk (works with any backend)."""
    import matplotlib.pyplot as plt

    h = result.history
    ticks = [s.tick for s in h]

    fig, ax = plt.subplots(figsize=(13, 6))

    ax.stackplot(
        ticks,
        [s.normal for s in h],
        [s.gene_drive for s in h],
        [s.sterile for s in h],
        [s.resistant for s in h],
        labels=["Normal Mosquitoes", "Gene-Drive Carriers",
                "Sterile Mosquitoes", "Resistant Mosquitoes"],
        colors=[_COLORS["normal"], _COLORS["gene_drive"],
                _COLORS["sterile"], _COLORS["resistant"]],
        alpha=0.78,
    )
    ax.plot(ticks, [s.frogs for s in h], "-",
            color=_COLORS["frogs"], linewidth=2.5, label="Frogs", zorder=5)

    ax.axvline(result.gene_drive_release_tick,
               color=_COLORS["drive_line"], linestyle="--", linewidth=2, alpha=0.9,
               label=f"Drive Release (tick {result.gene_drive_release_tick})")

    if result.resistance_tick is not None:
        ax.axvline(result.resistance_tick,
                   color=_COLORS["resist_line"], linestyle=":", linewidth=2, alpha=0.9,
                   label=f"Resistance Emerges (tick {result.resistance_tick})")

    # Outcome annotations
    last_tick = ticks[-1] if ticks else 0
    if result.frog_extinction:
        ax.annotate("FROGS\nEXTINCT", xy=(last_tick, 2),
                    fontsize=8, color=_COLORS["frogs"], fontstyle="italic",
                    xytext=(-90, 30), textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", color=_COLORS["frogs"]))
    if result.mosquito_extinction:
        ax.annotate("MOSQUITOES\nEXTINCT", xy=(last_tick, 6),
                    fontsize=8, color=_COLORS["normal"], fontstyle="italic",
                    xytext=(-130, 55), textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", color=_COLORS["normal"]))

    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("Gene Drive Ecosystem Simulation — Summary", fontsize=13, pad=10)
    ax.set_xlabel("Simulation Tick", fontsize=11)
    ax.set_ylabel("Population Count", fontsize=11)

    fig.tight_layout()
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
