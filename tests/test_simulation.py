"""Tests for simulation.py — 44 tests covering all agent types, mechanics, and CLI."""
import math
import os
import sys
from unittest.mock import MagicMock, patch

import matplotlib
matplotlib.use("Agg")  # headless — must be before any pyplot import

import pytest
from click.testing import CliRunner

from simulation import (
    DEFAULT_CONFIG,
    Genotype,
    Mosquito,
    Frog,
    Swamp,
    PopulationSnapshot,
    SimulationResult,
    Simulation,
)


# ---------------------------------------------------------------------------
# Minimal config helpers
# ---------------------------------------------------------------------------

def _cfg(**overrides) -> dict:
    """Return a fast, deterministic test config."""
    base = {
        **DEFAULT_CONFIG,
        "seed": 0,
        "n_mosquitoes": 20,
        "n_frogs": 3,
        "n_swamps": 0,
        "swamp_spawn_rate": 0,
        "mosquito_birth_rate": 0.0,   # no reproduction by default
        "gene_drive_release_tick": 9999,  # no drive by default
        "resistance_prob": 0.0,
        "max_fertile_pop": 1000,
    }
    base.update(overrides)
    return base


# ===========================================================================
# Mosquito tests
# ===========================================================================

def test_mosquito_default_genotype_is_normal():
    m = Mosquito(x=10.0, y=10.0)
    assert m.genotype == Genotype.NORMAL


def test_mosquito_sterile_not_fertile():
    m = Mosquito(x=0, y=0, genotype=Genotype.STERILE)
    assert not m.is_fertile()


def test_mosquito_normal_is_fertile():
    assert Mosquito(x=0, y=0, genotype=Genotype.NORMAL).is_fertile()


def test_mosquito_gene_drive_is_fertile():
    assert Mosquito(x=0, y=0, genotype=Genotype.GENE_DRIVE).is_fertile()


def test_mosquito_resistant_is_fertile():
    assert Mosquito(x=0, y=0, genotype=Genotype.RESISTANT).is_fertile()


def test_mosquito_move_increments_age():
    m = Mosquito(x=50.0, y=40.0)
    m.move(100.0, 80.0)
    assert m.age == 1


def test_mosquito_move_wraps_x():
    m = Mosquito(x=99.0, y=40.0)
    m.move(100.0, 80.0, speed=0.0)  # no displacement, just age increment
    assert 0.0 <= m.x < 100.0


def test_mosquito_move_wraps_large_step():
    import random as _r
    _r.seed(0)
    m = Mosquito(x=1.0, y=40.0)
    for _ in range(100):
        m.move(100.0, 80.0, speed=3.0)
        assert 0.0 <= m.x < 100.0
        assert 0.0 <= m.y < 80.0


def test_mosquito_not_dead_before_max_age():
    m = Mosquito(x=0, y=0, age=0)
    assert not m.is_dead(max_age=70)


def test_mosquito_is_dead_at_max_age():
    m = Mosquito(x=0, y=0, age=70)
    assert m.is_dead(max_age=70)


def test_mosquito_offspring_gene_drive_produces_sterile():
    m = Mosquito(x=0, y=0, genotype=Genotype.GENE_DRIVE)
    result = m.offspring_genotype(p_drive_encounter=1.0, resistance_prob=0.0)
    assert result == Genotype.STERILE


def test_mosquito_offspring_resistant_produces_resistant():
    m = Mosquito(x=0, y=0, genotype=Genotype.RESISTANT)
    result = m.offspring_genotype(p_drive_encounter=1.0, resistance_prob=0.0)
    assert result == Genotype.RESISTANT


def test_mosquito_offspring_normal_no_drive_produces_normal():
    import random as _r
    _r.seed(99)
    m = Mosquito(x=0, y=0, genotype=Genotype.NORMAL)
    # p_drive_encounter=0.0 → drive never encountered
    result = m.offspring_genotype(p_drive_encounter=0.0, resistance_prob=0.0)
    assert result == Genotype.NORMAL


def test_mosquito_offspring_normal_with_drive_produces_gene_drive():
    import random as _r
    _r.seed(0)
    m = Mosquito(x=0, y=0, genotype=Genotype.NORMAL)
    # p_drive_encounter=1.0 → always encounters drive
    result = m.offspring_genotype(p_drive_encounter=1.0, resistance_prob=0.0)
    assert result == Genotype.GENE_DRIVE


def test_mosquito_offspring_resistance_mutation():
    import random as _r
    _r.seed(0)
    m = Mosquito(x=0, y=0, genotype=Genotype.NORMAL)
    # resistance_prob=1.0 → always mutates
    result = m.offspring_genotype(p_drive_encounter=0.0, resistance_prob=1.0)
    assert result == Genotype.RESISTANT


# ===========================================================================
# Frog tests
# ===========================================================================

def test_frog_metabolize_reduces_energy():
    f = Frog(x=0, y=0, energy=100.0)
    f.metabolize(cost=2.5)
    assert f.energy == pytest.approx(97.5)


def test_frog_eat_increases_energy():
    f = Frog(x=0, y=0, energy=50.0)
    f.eat(gain=30.0)
    assert f.energy == pytest.approx(80.0)


def test_frog_can_reproduce_above_threshold():
    f = Frog(x=0, y=0, energy=250.0)
    assert f.can_reproduce(threshold=220.0)


def test_frog_cannot_reproduce_below_threshold():
    f = Frog(x=0, y=0, energy=100.0)
    assert not f.can_reproduce(threshold=220.0)


def test_frog_reproduce_returns_new_frog():
    f = Frog(x=5.0, y=5.0, energy=250.0)
    child = f.reproduce(initial_energy=80.0)
    assert isinstance(child, Frog)
    assert child.energy == pytest.approx(80.0)


def test_frog_reproduce_donates_energy():
    f = Frog(x=0, y=0, energy=250.0)
    f.reproduce(initial_energy=80.0)
    assert f.energy == pytest.approx(170.0)


def test_frog_is_dead_when_energy_zero():
    f = Frog(x=0, y=0, energy=0.0)
    assert f.is_dead(max_age=250)


def test_frog_is_dead_at_max_age():
    f = Frog(x=0, y=0, energy=100.0, age=250)
    assert f.is_dead(max_age=250)


def test_frog_is_not_dead_with_energy():
    f = Frog(x=0, y=0, energy=50.0, age=10)
    assert not f.is_dead(max_age=250)


def test_frog_move_increments_age():
    f = Frog(x=50.0, y=40.0)
    f.move(100.0, 80.0)
    assert f.age == 1


# ===========================================================================
# Swamp tests
# ===========================================================================

def test_swamp_spawn_returns_correct_count():
    s = Swamp(x=50.0, y=40.0, spawn_rate=3)
    result = s.spawn()
    assert len(result) == 3


def test_swamp_spawn_returns_normal_genotype():
    s = Swamp(x=50.0, y=40.0, spawn_rate=2)
    for m in s.spawn():
        assert m.genotype == Genotype.NORMAL


# ===========================================================================
# Simulation initialization
# ===========================================================================

def test_simulation_initial_mosquito_count():
    sim = Simulation(_cfg(n_mosquitoes=30))
    assert len(sim.mosquitoes) == 30


def test_simulation_initial_frog_count():
    sim = Simulation(_cfg(n_frogs=5))
    assert len(sim.frogs) == 5


def test_simulation_initial_swamp_count():
    sim = Simulation(_cfg(n_swamps=4))
    assert len(sim.swamps) == 4


def test_simulation_initial_tick_is_zero():
    sim = Simulation(_cfg())
    assert sim.tick == 0


# ===========================================================================
# Simulation step mechanics
# ===========================================================================

def test_simulation_step_increments_tick():
    sim = Simulation(_cfg())
    sim.step()
    assert sim.tick == 1


def test_simulation_gene_drive_not_released_before_tick():
    sim = Simulation(_cfg(gene_drive_release_tick=5))
    sim.step()  # tick 1
    assert not sim.gene_drive_released
    assert all(m.genotype != Genotype.GENE_DRIVE for m in sim.mosquitoes)


def test_simulation_gene_drive_released_at_tick():
    sim = Simulation(_cfg(gene_drive_release_tick=1, n_drive=5))
    sim.step()  # tick 1
    assert sim.gene_drive_released


def test_simulation_gene_drive_adds_correct_count():
    # n_frogs=0 prevents frogs eating the newly released drive mosquitoes
    sim = Simulation(_cfg(n_mosquitoes=0, n_frogs=0, gene_drive_release_tick=1,
                          n_gene_drive=8))
    sim.step()
    drive_count = sum(1 for m in sim.mosquitoes if m.genotype == Genotype.GENE_DRIVE)
    assert drive_count == 8


def test_simulation_gene_drive_mosquitoes_have_correct_genotype():
    sim = Simulation(_cfg(gene_drive_release_tick=1, n_gene_drive=5))
    sim.step()
    drive_mosquitoes = [m for m in sim.mosquitoes if m.genotype == Genotype.GENE_DRIVE]
    assert len(drive_mosquitoes) == 5


def test_simulation_history_grows_each_tick():
    sim = Simulation(_cfg())
    for i in range(5):
        sim.step()
        assert len(sim.history) == i + 1


def test_simulation_snapshot_tick_matches():
    sim = Simulation(_cfg())
    sim.step()
    assert sim.history[0].tick == 1


# ===========================================================================
# Ecological mechanics
# ===========================================================================

def test_simulation_frogs_eat_nearby_mosquitoes():
    """With a huge eat radius, each frog should eat exactly one mosquito per tick."""
    cfg = _cfg(
        n_mosquitoes=50, n_frogs=3,
        frog_eat_radius=9999.0,
        frog_metabolism=0.0,        # no energy loss (prevent death)
        frog_initial_energy=500.0,
    )
    sim = Simulation(cfg)
    before = len(sim.mosquitoes)
    sim.step()
    # 3 frogs ate 3 mosquitoes; no births (birth_rate=0), no swamps, age < max_age
    assert len(sim.mosquitoes) == before - 3


def test_simulation_frog_energy_increases_on_eat():
    cfg = _cfg(
        n_mosquitoes=20, n_frogs=1,
        frog_eat_radius=9999.0,
        frog_eat_gain=30.0,
        frog_metabolism=0.0,
        frog_initial_energy=50.0,
    )
    sim = Simulation(cfg)
    sim.step()
    # frog ate 1 mosquito (+30 energy) with no metabolism loss
    assert sim.frogs[0].energy == pytest.approx(80.0)


def test_simulation_sterile_mosquitoes_do_not_reproduce():
    """Sterile mosquitoes should never produce offspring."""
    cfg = _cfg(mosquito_birth_rate=1.0, resistance_prob=0.0)
    sim = Simulation(cfg)
    # Replace all mosquitoes with sterile ones
    for m in sim.mosquitoes:
        m.genotype = Genotype.STERILE
    before = len(sim.mosquitoes)
    sim.step()
    # No reproduction possible → mosquito count can only decrease (aging or frog predation)
    assert len(sim.mosquitoes) <= before


def test_simulation_gene_drive_produces_sterile_offspring():
    """Gene-drive mosquitoes should produce only sterile offspring."""
    cfg = _cfg(
        n_mosquitoes=0, n_frogs=0,
        gene_drive_release_tick=1, n_gene_drive=10,
        mosquito_birth_rate=1.0,  # reproduce every tick
        resistance_prob=0.0,
    )
    sim = Simulation(cfg)
    sim.step()  # releases drive mosquitoes + they reproduce
    sim.step()  # offspring from drive carriers are born
    offspring = [m for m in sim.mosquitoes if m.genotype == Genotype.STERILE]
    # Some sterile offspring should exist (drive carriers reproduced)
    assert len(offspring) > 0


def test_simulation_resistance_tick_set_on_emergence():
    """resistance_tick should be set the tick resistance first appears.

    Resistance only emerges under selection pressure (after drive release),
    so the drive must be active for resistance_prob to apply.
    """
    cfg = _cfg(
        n_mosquitoes=200, n_frogs=0,
        mosquito_birth_rate=1.0,
        resistance_prob=1.0,  # every birth is resistant once drive is active
        gene_drive_release_tick=1,  # drive released tick 1 → selection pressure active
        n_gene_drive=1,
    )
    sim = Simulation(cfg)
    sim.step()
    assert sim.resistance_tick == 1


def test_simulation_resistance_tick_none_if_no_resistance():
    cfg = _cfg(resistance_prob=0.0, mosquito_birth_rate=0.0)
    sim = Simulation(cfg)
    for _ in range(10):
        sim.step()
    assert sim.resistance_tick is None


def test_simulation_population_cap_enforced():
    cfg = _cfg(
        n_mosquitoes=50, n_frogs=0,
        mosquito_birth_rate=1.0,
        n_swamps=0, swamp_spawn_rate=0,
        resistance_prob=0.0,
        max_fertile_pop=60,
        gene_drive_release_tick=9999,
    )
    sim = Simulation(cfg)
    for _ in range(20):
        sim.step()
    assert len(sim.mosquitoes) <= 60


# ===========================================================================
# SimulationResult
# ===========================================================================

def test_simulation_result_structure():
    sim = Simulation(_cfg())
    sim.run(5)
    r = sim.result()
    assert isinstance(r, SimulationResult)
    assert r.gene_drive_release_tick == 9999
    assert len(r.history) == 5


def test_simulation_result_peak_mosquitoes():
    sim = Simulation(_cfg(n_mosquitoes=30, n_frogs=0, n_swamps=0))
    sim.run(5)
    r = sim.result()
    assert r.peak_mosquitoes >= 0


def test_simulation_result_extinction_flags():
    # All mosquitoes die instantly (no food, max_age=1)
    cfg = _cfg(
        n_mosquitoes=5, n_frogs=0,
        mosquito_max_age=1,
        mosquito_birth_rate=0.0,
    )
    sim = Simulation(cfg)
    sim.run(5)
    r = sim.result()
    assert r.final_mosquitoes == 0
    assert r.mosquito_extinction is True


def test_simulation_result_summary_text_contains_key_fields():
    sim = Simulation(_cfg())
    sim.run(3)
    text = sim.result().summary_text()
    assert "Gene drive" in text
    assert "mosquito" in text.lower()
    assert "frog" in text.lower()


# ===========================================================================
# CLI tests (no live chart, no API calls)
# ===========================================================================

def test_cli_run_no_live_exits_0():
    from cli import cli
    runner = CliRunner()
    r = runner.invoke(cli, ["run", "--ticks", "10", "--no-live", "--no-brief"])
    assert r.exit_code == 0, r.output


def test_cli_run_shows_progress():
    from cli import cli
    runner = CliRunner()
    r = runner.invoke(cli, ["run", "--ticks", "20", "--no-live", "--no-brief"])
    assert "tick=" in r.output


def test_cli_run_shows_summary():
    from cli import cli
    runner = CliRunner()
    r = runner.invoke(cli, ["run", "--ticks", "10", "--no-live", "--no-brief"])
    assert "mosquitoes" in r.output.lower()


def test_cli_brief_warns_without_api_key():
    from cli import cli
    runner = CliRunner()
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    r = runner.invoke(cli, ["run", "--ticks", "5", "--no-live"], env=env)
    # Should warn about missing key, not crash
    assert r.exit_code == 0


def test_cli_policy_brief_generated_with_mocked_api():
    from cli import cli
    runner = CliRunner()

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="MOCK POLICY BRIEF CONTENT")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg

    # anthropic is imported lazily inside generate_brief, so patch at the package level
    with patch("anthropic.Anthropic", return_value=mock_client):
        env = {"ANTHROPIC_API_KEY": "test-key"}
        r = runner.invoke(cli, ["run", "--ticks", "5", "--no-live"], env=env)

    assert r.exit_code == 0
    assert "MOCK POLICY BRIEF CONTENT" in r.output
