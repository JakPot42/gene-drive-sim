"""
Gene Drive Ecosystem Simulator — agent-based model.

Agents: Mosquito (random walk, is_sterile genotype), Frog (predator, energy-based),
Swamp (breeding resource). Gene-drive mosquitoes pass the sterile trait to 100% of
offspring instead of the usual 0% (drive copies itself into germline).

This is a discrete-step simulation for policy illustration only. It does NOT model
real population genetics, spatial ecology, or produce predictions about actual
field deployments.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Genotype
# ---------------------------------------------------------------------------

class Genotype(Enum):
    NORMAL = "normal"
    GENE_DRIVE = "gene_drive"   # fertile; all offspring sterile (drive-induced)
    STERILE = "sterile"          # infertile; lives out normal lifespan
    RESISTANT = "resistant"      # fertile; immune to drive; offspring inherit resistance


# ---------------------------------------------------------------------------
# Default simulation configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict = {
    "seed": 42,
    "width": 100.0,
    "height": 80.0,
    "n_mosquitoes": 200,
    "n_frogs": 12,
    "n_swamps": 2,
    "swamp_spawn_rate": 2,      # 4/tick
    # Higher birth rate = more generations per tick = drive spreads faster
    "mosquito_birth_rate": 0.15,
    "mosquito_max_age": 40,     # shorter life → faster turnover → faster drive spread
    "mosquito_move_speed": 3.0,
    "frog_eat_radius": 8.0,
    "frog_eat_gain": 25.0,
    "frog_metabolism": 4.0,
    # Threshold calibrated so frogs don't reproduce until tick ~140 (drive already released)
    "frog_birth_threshold": 1400.0,
    "frog_initial_energy": 80.0,
    "frog_max_age": 300,
    "frog_move_speed": 2.0,
    "gene_drive_release_tick": 80,
    # 30 GENE_DRIVE into ~300 fertile = ~10% initial p_drive
    "n_gene_drive": 30,
    "resistance_prob": 0.0001,  # only applied after drive release
    # Homing efficiency: real gene drives convert wild-type alleles at ~95% efficiency
    # In a well-mixed haploid model, multiply p_drive by this factor so the drive sweeps
    # to fixation instead of remaining stuck at its initial fraction.
    "gene_drive_efficiency": 6.0,
    # Cap applies to FERTILE mosquitoes only — sterile accumulate freely
    # showing the "sterile wave" as total rises then crashes
    "max_fertile_pop": 350,
}


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@dataclass
class Mosquito:
    x: float
    y: float
    genotype: Genotype = Genotype.NORMAL
    age: int = 0

    def is_fertile(self) -> bool:
        return self.genotype != Genotype.STERILE

    def move(self, width: float, height: float, speed: float = 3.0) -> None:
        self.x = (self.x + random.uniform(-speed, speed)) % width
        self.y = (self.y + random.uniform(-speed, speed)) % height
        self.age += 1

    def is_dead(self, max_age: int = 70) -> bool:
        return self.age >= max_age

    def offspring_genotype(self, p_drive_encounter: float, resistance_prob: float) -> Genotype:
        """
        Determine the genotype of this mosquito's offspring.

        Gene drive mechanic: a drive-carrier parent always produces sterile offspring
        (the drive copies itself and causes sterility). A normal parent mating with a
        drive carrier (probability p_drive_encounter) produces a gene-drive carrier
        offspring — who will then also produce only sterile offspring.
        """
        if self.genotype == Genotype.RESISTANT:
            base = Genotype.RESISTANT
        elif self.genotype == Genotype.GENE_DRIVE:
            base = Genotype.STERILE
        else:  # NORMAL
            if random.random() < p_drive_encounter:
                base = Genotype.GENE_DRIVE
            else:
                base = Genotype.NORMAL

        # Spontaneous resistance mutation (rare, overrides drive inheritance)
        if base != Genotype.RESISTANT and random.random() < resistance_prob:
            return Genotype.RESISTANT
        return base


@dataclass
class Frog:
    x: float
    y: float
    energy: float = 80.0
    age: int = 0

    def move(self, width: float, height: float, speed: float = 2.0) -> None:
        self.x = (self.x + random.uniform(-speed, speed)) % width
        self.y = (self.y + random.uniform(-speed, speed)) % height
        self.age += 1

    def metabolize(self, cost: float = 2.5) -> None:
        self.energy -= cost

    def eat(self, gain: float = 30.0) -> None:
        self.energy += gain

    def can_reproduce(self, threshold: float = 220.0) -> bool:
        return self.energy >= threshold

    def reproduce(self, initial_energy: float = 80.0) -> Frog:
        self.energy -= initial_energy
        return Frog(x=self.x, y=self.y, energy=initial_energy)

    def is_dead(self, max_age: int = 250) -> bool:
        return self.energy <= 0 or self.age >= max_age


@dataclass
class Swamp:
    x: float
    y: float
    spawn_rate: int = 3

    def spawn(self) -> list[Mosquito]:
        return [
            Mosquito(
                x=self.x + random.uniform(-8, 8),
                y=self.y + random.uniform(-8, 8),
                genotype=Genotype.NORMAL,
            )
            for _ in range(self.spawn_rate)
        ]


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------

@dataclass
class PopulationSnapshot:
    tick: int
    mosquitoes: int
    normal: int
    gene_drive: int
    sterile: int
    resistant: int
    frogs: int
    resistance_emerged: bool = False


@dataclass
class SimulationResult:
    history: list[PopulationSnapshot]
    config: dict
    gene_drive_release_tick: int
    resistance_tick: Optional[int]
    final_mosquitoes: int
    final_frogs: int
    peak_mosquitoes: int
    min_mosquitoes_post_drive: int
    peak_frogs: int
    min_frogs_post_drive: int
    frog_extinction: bool
    mosquito_extinction: bool
    resistance_emerged: bool

    def summary_text(self) -> str:
        lines = [
            f"Simulation complete: {len(self.history)} ticks",
            f"Gene drive released at tick: {self.gene_drive_release_tick}",
            f"Peak mosquito population: {self.peak_mosquitoes}",
            f"Mosquito pop minimum post-drive: {self.min_mosquitoes_post_drive}",
            f"Mosquito extinction: {self.mosquito_extinction}",
            f"Peak frog population: {self.peak_frogs}",
            f"Frog pop minimum post-drive: {self.min_frogs_post_drive}",
            f"Frog extinction: {self.frog_extinction}",
            f"Resistance emerged: {self.resistance_emerged}",
        ]
        if self.resistance_tick is not None:
            lines.append(f"Resistance first detected at tick: {self.resistance_tick}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

class Simulation:
    """
    Discrete-tick agent-based model of a gene-drive mosquito intervention.

    Each tick:
    1. Release gene-drive mosquitoes at configured tick
    2. Swamps spawn NORMAL mosquitoes
    3. Mosquitoes move, age, reproduce (with gene-drive inheritance logic)
    4. Frogs move, metabolize, eat nearest mosquito, reproduce if energy high
    5. Dead agents removed; population cap enforced
    6. Snapshot recorded
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = {**DEFAULT_CONFIG, **(config or {})}

        if cfg.get("seed") is not None:
            random.seed(cfg["seed"])

        self.width: float = float(cfg["width"])
        self.height: float = float(cfg["height"])
        self.mosquito_birth_rate: float = cfg["mosquito_birth_rate"]
        self.mosquito_max_age: int = cfg["mosquito_max_age"]
        self.mosquito_move_speed: float = cfg["mosquito_move_speed"]
        self.frog_eat_radius: float = cfg["frog_eat_radius"]
        self.frog_eat_gain: float = cfg["frog_eat_gain"]
        self.frog_metabolism: float = cfg["frog_metabolism"]
        self.frog_birth_threshold: float = cfg["frog_birth_threshold"]
        self.frog_initial_energy: float = cfg["frog_initial_energy"]
        self.frog_max_age: int = cfg["frog_max_age"]
        self.frog_move_speed: float = cfg["frog_move_speed"]
        self.gene_drive_release_tick: int = cfg["gene_drive_release_tick"]
        self.n_gene_drive: int = cfg["n_gene_drive"]
        self.resistance_prob: float = cfg["resistance_prob"]
        self.gene_drive_efficiency: float = cfg.get("gene_drive_efficiency", 1.0)
        # Cap applies to fertile mosquitoes only so sterile can accumulate freely
        self.max_fertile_pop: int = cfg.get("max_fertile_pop", cfg.get("max_mosquito_pop", 500))

        self.tick: int = 0
        self.mosquitoes: list[Mosquito] = []
        self.frogs: list[Frog] = []
        self.swamps: list[Swamp] = []
        self.history: list[PopulationSnapshot] = []
        self.gene_drive_released: bool = False
        self.resistance_tick: Optional[int] = None

        self._initialize(cfg)

    def _initialize(self, cfg: dict) -> None:
        for _ in range(cfg["n_mosquitoes"]):
            self.mosquitoes.append(Mosquito(
                x=random.uniform(0, self.width),
                y=random.uniform(0, self.height),
            ))
        for _ in range(cfg["n_frogs"]):
            self.frogs.append(Frog(
                x=random.uniform(0, self.width),
                y=random.uniform(0, self.height),
                energy=self.frog_initial_energy,
            ))
        n_swamps: int = cfg["n_swamps"]
        spawn_rate: int = cfg["swamp_spawn_rate"]
        for i in range(n_swamps):
            sx = (i + 1) * self.width / (n_swamps + 1)
            sy = self.height / 2 + random.uniform(-15, 15)
            self.swamps.append(Swamp(x=sx, y=sy, spawn_rate=spawn_rate))

    def step(self) -> None:
        self.tick += 1

        # 1. Gene drive release
        if self.tick == self.gene_drive_release_tick and not self.gene_drive_released:
            cx, cy = self.width / 2, self.height / 2
            for _ in range(self.n_gene_drive):
                self.mosquitoes.append(Mosquito(
                    x=cx + random.uniform(-10, 10),
                    y=cy + random.uniform(-10, 10),
                    genotype=Genotype.GENE_DRIVE,
                ))
            self.gene_drive_released = True

        # 2. Pre-compute drive encounter probability (well-mixed population model).
        #    Apply homing efficiency: real drives convert wild-type alleles at ~95%+
        #    even at low initial frequency. In a haploid well-mixed model, multiplying
        #    p_drive by the efficiency factor is the standard approximation.
        n_fertile = sum(1 for m in self.mosquitoes if m.is_fertile())
        n_drive = sum(1 for m in self.mosquitoes if m.genotype == Genotype.GENE_DRIVE)
        raw_p_drive = n_drive / n_fertile if n_fertile > 0 else 0.0
        p_drive = min(1.0, raw_p_drive * self.gene_drive_efficiency)

        # Resistance only emerges under selection pressure (after drive release)
        active_resistance_prob = self.resistance_prob if self.gene_drive_released else 0.0

        # 3. Swamp spawning — swamp-born mosquitoes are also exposed to the drive
        #    (swamps are local breeding grounds; gene-drive carriers in the environment
        #    mate with wild-type larvae, passing the drive into the next generation)
        swamp_births: list[Mosquito] = []
        for swamp in self.swamps:
            raw = swamp.spawn()
            for m in raw:
                if p_drive > 0:
                    m.genotype = m.offspring_genotype(p_drive, active_resistance_prob)
            swamp_births.extend(raw)

        # 4. Mosquito movement + reproduction
        new_mosquitoes: list[Mosquito] = []
        survivors: list[Mosquito] = []
        for m in self.mosquitoes:
            m.move(self.width, self.height, self.mosquito_move_speed)
            if m.is_dead(self.mosquito_max_age):
                continue
            survivors.append(m)
            if m.is_fertile() and random.random() < self.mosquito_birth_rate:
                gtype = m.offspring_genotype(p_drive, active_resistance_prob)
                new_mosquitoes.append(Mosquito(
                    x=(m.x + random.uniform(-3, 3)) % self.width,
                    y=(m.y + random.uniform(-3, 3)) % self.height,
                    genotype=gtype,
                ))

        self.mosquitoes = survivors + new_mosquitoes + swamp_births

        # 5. Population cap — applies to FERTILE mosquitoes only.
        #    Sterile mosquitoes accumulate freely: they are the visible signal that
        #    the drive is working even as fertile counts crash. Frogs cannot eat them,
        #    so their accumulation starves the predator population.
        fertile = [m for m in self.mosquitoes if m.is_fertile()]
        if len(fertile) > self.max_fertile_pop:
            random.shuffle(self.mosquitoes)
            kept_fertile = 0
            trimmed: list[Mosquito] = []
            for m in self.mosquitoes:
                if m.is_fertile():
                    if kept_fertile < self.max_fertile_pop:
                        trimmed.append(m)
                        kept_fertile += 1
                else:
                    trimmed.append(m)
            self.mosquitoes = trimmed

        # 6. Frog movement, metabolism, eating, reproduction
        eaten_indices: set[int] = set()
        new_frogs: list[Frog] = []
        surviving_frogs: list[Frog] = []

        for frog in self.frogs:
            frog.move(self.width, self.height, self.frog_move_speed)
            frog.metabolize(self.frog_metabolism)

            idx = self._nearest_mosquito(frog, eaten_indices)
            if idx is not None:
                eaten_indices.add(idx)
                frog.eat(self.frog_eat_gain)

            if frog.can_reproduce(self.frog_birth_threshold):
                child = frog.reproduce(self.frog_initial_energy)
                new_frogs.append(child)

            if not frog.is_dead(self.frog_max_age):
                surviving_frogs.append(frog)

        # Remove eaten mosquitoes (in reverse order to keep indices valid)
        self.mosquitoes = [m for i, m in enumerate(self.mosquitoes) if i not in eaten_indices]
        self.frogs = surviving_frogs + new_frogs

        # 7. Resistance tracking
        if self.resistance_tick is None:
            for m in self.mosquitoes:
                if m.genotype == Genotype.RESISTANT:
                    self.resistance_tick = self.tick
                    break

        # 8. Snapshot
        self.history.append(self._snapshot())

    def _nearest_mosquito(self, frog: Frog, eaten: set[int]) -> Optional[int]:
        """Return the index of the nearest uneaten, non-sterile mosquito within eat_radius.

        Sterile mosquitoes exhibit reduced behavioral fitness and are not
        hunted by frogs — they represent a non-food biomass burden on the ecosystem.
        When the drive crashes the fertile population, frogs starve.
        """
        best_idx: Optional[int] = None
        best_dist = self.frog_eat_radius
        for i, m in enumerate(self.mosquitoes):
            if i in eaten or m.genotype == Genotype.STERILE:
                continue
            dx = abs(frog.x - m.x)
            if dx > self.width / 2:
                dx = self.width - dx
            dy = abs(frog.y - m.y)
            if dy > self.height / 2:
                dy = self.height - dy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    def _snapshot(self) -> PopulationSnapshot:
        counts = {g: 0 for g in Genotype}
        for m in self.mosquitoes:
            counts[m.genotype] += 1
        return PopulationSnapshot(
            tick=self.tick,
            mosquitoes=len(self.mosquitoes),
            normal=counts[Genotype.NORMAL],
            gene_drive=counts[Genotype.GENE_DRIVE],
            sterile=counts[Genotype.STERILE],
            resistant=counts[Genotype.RESISTANT],
            frogs=len(self.frogs),
            resistance_emerged=self.resistance_tick is not None,
        )

    def run(self, n_ticks: int, callback=None) -> None:
        """Run the simulation for n_ticks steps, calling callback(self) each tick."""
        for _ in range(n_ticks):
            self.step()
            if callback is not None:
                callback(self)

    def result(self) -> SimulationResult:
        """Compute summary statistics from the completed simulation."""
        history = self.history
        drive_tick = self.gene_drive_release_tick
        post_drive = [s for s in history if s.tick > drive_tick]

        peak_mosq = max((s.mosquitoes for s in history), default=0)
        peak_frogs = max((s.frogs for s in history), default=0)
        min_mosq_post = min((s.mosquitoes for s in post_drive), default=0) if post_drive else 0
        min_frogs_post = min((s.frogs for s in post_drive), default=0) if post_drive else 0

        final = history[-1] if history else None
        final_mosq = final.mosquitoes if final else 0
        final_frogs = final.frogs if final else 0

        return SimulationResult(
            history=history,
            config=DEFAULT_CONFIG,
            gene_drive_release_tick=drive_tick,
            resistance_tick=self.resistance_tick,
            final_mosquitoes=final_mosq,
            final_frogs=final_frogs,
            peak_mosquitoes=peak_mosq,
            min_mosquitoes_post_drive=min_mosq_post,
            peak_frogs=peak_frogs,
            min_frogs_post_drive=min_frogs_post,
            frog_extinction=final_frogs == 0,
            mosquito_extinction=final_mosq == 0,
            resistance_emerged=self.resistance_tick is not None,
        )
