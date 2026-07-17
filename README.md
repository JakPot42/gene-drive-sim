# Gene Drive Ecosystem Simulator + Policy Brief

Agent-based model of a gene-drive mosquito intervention and its unintended ecological consequences.
After each run, **Claude generates a policy brief** connecting the simulation outcomes to real
gene drive research (Target Malaria, DARPA Safe Genes, WHO Guidance Framework for GDOs).

---

## What It Simulates

**Agents:**
| Agent | Behaviour |
|-------|-----------|
| Mosquito | Random walk, `NORMAL / GENE_DRIVE / STERILE / RESISTANT` genotype |
| Frog | Energy-based predator; eats nearest mosquito in range, starves without food |
| Swamp | Breeding resource; spawns `NORMAL` mosquitoes every tick |

**Gene Drive Mechanic:**
A gene-drive carrier passes the sterile trait to **100% of its offspring** (vs. 0% for wild-type),
modelling the homing endonuclease mechanism used in projects like Target Malaria. Exposed wild-type
mosquitoes whose offspring inherit the drive also produce only sterile offspring — creating a
population-level cascade. A homing efficiency multiplier approximates real-drive conversion rates
(>95% in lab studies).

**Three Possible Outcomes (stochastic):**
1. **Mosquito crash** — sterile population swamps fertile ones; reproduction collapses
2. **Frog starvation** — trophic cascade; frogs lose food source and population crashes
3. **Resistance emergence** — spontaneous mutation shields a lineage from the drive

---

## Usage

```bash
pip install -r requirements.txt

# Demo: live chart + policy brief (requires ANTHROPIC_API_KEY)
py cli.py demo

# Custom run, no live chart, no brief (headless / CI)
py cli.py run --ticks 500 --no-live --no-brief

# Custom parameters
py cli.py run --ticks 600 --drive-tick 100 --n-drive 20 --resistance-prob 0.001

# Save plot to custom path
py cli.py run --ticks 500 --no-live --no-brief --output results/run1.png
```

Set `ANTHROPIC_API_KEY` to enable policy brief generation.

---

## Demo Output

```
Running 500 ticks (gene drive at tick 80)...
  [ 16.0%] tick=  80  mosquitoes= 350  frogs= 19  <- drive released
  [ 18.0%] tick=  90  mosquitoes= 535  frogs= 22  <- sterile wave building
  [ 20.0%] tick= 100  mosquitoes= 879  frogs= 25
  [ 24.0%] tick= 120  mosquitoes=1610  frogs= 32  <- peak: 1635 total (93% sterile)
  [ 28.0%] tick= 140  mosquitoes=1304  frogs= 38  <- fertile crashing
  [ 32.0%] tick= 160  mosquitoes= 521  frogs= 40  <- fertile near zero
  [ 36.0%] tick= 180  mosquitoes=  95  frogs= 41  <- fertile=0; frogs have no food
  [ 40.0%] tick= 200  mosquitoes=   8  frogs= 37  <- frog starvation begins
  [ 60.0%] tick= 300  mosquitoes=   0  frogs= 25
  [ 80.0%] tick= 400  mosquitoes= 338  frogs= 17  <- swamp recovery; frogs at minimum
  [100.0%] tick= 500  mosquitoes= 342  frogs= 39  <- new equilibrium

  Simulation Results
  ----------------------------------------
  Simulation complete: 500 ticks
  Gene drive released at tick: 80
  Peak mosquito population: 1657
  Mosquito pop minimum post-drive: 0
  Mosquito extinction: False
  Peak frog population: 44
  Frog pop minimum post-drive: 13
  Frog extinction: False
  Resistance emerged: True
  Resistance first detected at tick: 91

  Plot saved: sim_output.png

  Generating policy brief (Claude Haiku)...
===================================================================
  POLICY BRIEF
===================================================================
  EXECUTIVE SUMMARY
  ...
```

**What this run shows:** The gene drive sweeps NORMAL mosquitoes to zero within 40 ticks of
release. A sterile wave peaks at 1,657 total mosquitoes (1,350+ sterile, inedible by frogs).
Fertile prey crashes to zero — frogs decline from 44 to a minimum of 13 (70% crash). The
ecosystem recovers only once swamps re-seed NORMAL mosquitoes over hundreds of ticks.
A resistance mutation appeared at tick 91 but failed to establish a population.

---

## Policy Brief Content

Claude is prompted to:
- Summarize what the simulation showed (quantitative)
- Analyse the **trophic cascade** (frog starvation as unintended consequence)
- Connect to **Target Malaria** (Anopheles gambiae CRISPR drive)
- Reference **DARPA Safe Genes** (reversibility research)
- Cite the **WHO Guidance Framework for Testing GDOs (2021)**
- Discuss **daisy chain drives** (Kevin Esvelt — geographically self-limiting alternative)
- Raise **policy considerations**: regulatory frameworks, FPIC of affected communities,
  island vs. continental deployment risk tiers

---

## Honest Limitations

This is a discrete-tick agent-based model for **policy illustration only**:
- Not a validated ecological model — parameters are illustrative, not field-calibrated
- Does not model real mosquito population genetics, spatial ecology, or actual drive dynamics
- A PASS (no crash) in this simulation says nothing about real field outcomes
- The trophic cascade shown is a simplified two-level predator-prey system

Real gene drive risk assessment requires validated compartmental models (e.g. Deredec et al. 2011,
Noble et al. 2019) and ecological network analysis — not toy ABMs.

---

## Running Tests

```bash
pytest tests/ -v
```

54 tests, all passing. No display required. No API calls.

---

## Tech Stack

- **Simulation:** Pure Python ABM (no external simulation library)
- **Visualization:** Matplotlib (live chart + saved summary plot)
- **Policy Brief:** Claude Haiku (`claude-haiku-4-5-20251001`)
- **CLI:** Click

## Architecture

```
simulation.py    <- Genotype, Mosquito, Frog, Swamp, Simulation, SimulationResult
visualizer.py    <- LiveVisualizer, save_summary_plot (lazy matplotlib imports)
policy_brief.py  <- generate_brief (Claude Haiku)
cli.py           <- Click CLI (run, demo)
tests/           <- pytest suite (simulation only, matplotlib mocked with Agg)
```
