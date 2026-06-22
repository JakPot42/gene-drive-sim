"""
Gene Drive Ecosystem Simulator CLI.
"""
from __future__ import annotations

import sys

import click

from simulation import DEFAULT_CONFIG, Simulation


@click.group()
def cli() -> None:
    """Gene Drive Ecosystem Simulator + Policy Brief Generator.

    Agent-based model: mosquitoes (random walk, sterile-trait genetics), frogs
    (energy-based predators), swamps (breeding resources). A gene-drive mosquito
    passes the sterile trait to 100% of offspring, potentially crashing the
    population — and starving the frogs that depend on it.

    After the run, Claude generates a policy brief connecting the simulated
    outcomes to real gene drive debates (Target Malaria, DARPA Safe Genes, etc.).
    """


@cli.command()
@click.option("--ticks", default=400, show_default=True, help="Simulation length in ticks.")
@click.option("--seed", default=42, show_default=True, help="Random seed for reproducibility.")
@click.option("--drive-tick", default=80, show_default=True,
              help="Tick at which gene-drive mosquitoes are released.")
@click.option("--n-drive", default=DEFAULT_CONFIG["n_gene_drive"], show_default=True,
              help="Number of gene-drive mosquitoes released.")
@click.option("--resistance-prob", default=DEFAULT_CONFIG["resistance_prob"], show_default=True,
              help="Per-birth probability of spontaneous resistance mutation.")
@click.option("--output", default="sim_output.png", show_default=True,
              help="Path to save the summary plot.")
@click.option("--live/--no-live", default=False,
              help="Show live-updating chart during simulation (requires display).")
@click.option("--no-brief", is_flag=True, default=False,
              help="Skip Claude policy brief generation.")
def run(ticks: int, seed: int, drive_tick: int, n_drive: int,
        resistance_prob: float, output: str, live: bool, no_brief: bool) -> None:
    """Run the simulation with custom parameters."""
    _run_simulation(
        ticks=ticks, seed=seed, drive_tick=drive_tick, n_drive=n_drive,
        resistance_prob=resistance_prob, output=output,
        live=live, no_brief=no_brief,
    )


@cli.command()
def demo() -> None:
    """Run with default parameters, live chart, and policy brief.

    Uses seed=42 for a reproducible demo that shows mosquito collapse,
    frog starvation, and potential resistance emergence.
    """
    click.echo("\nGene Drive Ecosystem Simulator — Demo Run")
    click.echo("=" * 55)
    click.echo(f"Default config: {DEFAULT_CONFIG['n_mosquitoes']} mosquitoes, "
               f"{DEFAULT_CONFIG['n_frogs']} frogs, {DEFAULT_CONFIG['n_swamps']} swamps")
    click.echo(f"Drive release at tick 80 ({DEFAULT_CONFIG['n_gene_drive']} gene-drive mosquitoes)")
    click.echo(f"Resistance probability: {DEFAULT_CONFIG['resistance_prob']} per birth")
    click.echo("=" * 55)

    _run_simulation(
        ticks=400, seed=42, drive_tick=DEFAULT_CONFIG["gene_drive_release_tick"],
        n_drive=DEFAULT_CONFIG["n_gene_drive"],
        resistance_prob=DEFAULT_CONFIG["resistance_prob"], output="sim_output.png",
        live=True, no_brief=False,
    )


def _run_simulation(
    ticks: int, seed: int, drive_tick: int, n_drive: int,
    resistance_prob: float, output: str, live: bool, no_brief: bool,
) -> None:
    # Configure backend BEFORE any pyplot import
    if not live:
        import matplotlib
        matplotlib.use("Agg")

    cfg = {
        **DEFAULT_CONFIG,
        "seed": seed,
        "gene_drive_release_tick": drive_tick,
        "n_gene_drive": n_drive,
        "resistance_prob": resistance_prob,
    }

    sim = Simulation(cfg)

    # Set up live visualizer
    viz = None
    if live:
        try:
            from visualizer import LiveVisualizer
            viz = LiveVisualizer()
        except Exception as exc:
            click.secho(
                f"  Warning: live chart unavailable ({exc}). "
                "Saving plot only.\n",
                fg="yellow", err=True,
            )
            live = False

    # Run
    click.echo(f"\nRunning {ticks} ticks (gene drive at tick {drive_tick})...")

    update_interval = max(1, ticks // 100)

    def callback(s: Simulation) -> None:
        if s.tick % update_interval == 0:
            pct = s.tick / ticks * 100
            n_mosq = len(s.mosquitoes)
            n_frog = len(s.frogs)
            click.echo(
                f"  [{pct:5.1f}%] tick={s.tick:4d}  "
                f"mosquitoes={n_mosq:4d}  frogs={n_frog:3d}",
                nl=True,
            )
        if viz is not None and s.tick % 5 == 0:
            viz.update(s)

    sim.run(ticks, callback=callback)

    result = sim.result()

    # Print summary
    click.echo()
    click.secho("  Simulation Results", bold=True)
    click.echo("  " + "-" * 40)
    for line in result.summary_text().splitlines():
        color = "red" if "extinction: True" in line else None
        color = "green" if "extinction: False" in line else color
        color = "magenta" if "Resistance emerged: True" in line else color
        click.secho(f"  {line}", fg=color)

    # Save plot
    click.echo()
    try:
        from visualizer import save_summary_plot
        save_summary_plot(result, output)
        click.secho(f"  Plot saved: {output}", fg="cyan")
    except Exception as exc:
        click.secho(f"  Warning: could not save plot ({exc})", fg="yellow", err=True)

    # Keep live chart open
    if viz is not None:
        viz.update(sim)
        click.echo("  (Close the chart window to continue.)")
        viz.keep_open()
        viz.close()

    # Policy brief
    if not no_brief:
        click.echo()
        click.secho("  Generating policy brief (Claude Haiku)...", fg="cyan")
        try:
            from policy_brief import generate_brief
            brief = generate_brief(result)
            click.echo()
            click.echo("=" * 65)
            click.secho("  POLICY BRIEF", bold=True)
            click.echo("=" * 65)
            click.echo(brief)
            click.echo("=" * 65)
        except RuntimeError as exc:
            click.secho(f"  {exc}", fg="yellow", err=True)
            click.echo("  Set ANTHROPIC_API_KEY to generate a policy brief.")
        except Exception as exc:
            click.secho(f"  Brief generation failed: {exc}", fg="red", err=True)

    click.echo()
    sys.exit(0)


if __name__ == "__main__":
    cli()
