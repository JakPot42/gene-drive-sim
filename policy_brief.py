"""
Claude-generated policy brief analyzing simulated gene drive ecological outcomes.
Connects simulation results to real gene drive research (Target Malaria, DARPA Safe Genes,
WHO Guidance Framework for GDOs, Kevin Esvelt's daisy chain drives).
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulation import SimulationResult

_SYSTEM_PROMPT = """\
You are an ecological policy analyst specializing in gene drives, biosafety, and environmental risk.
You have been given the statistical results of an agent-based simulation modeling a gene-drive
mosquito intervention and its ecological cascade effects.

Write a structured policy brief analyzing the simulated scenario. Connect the simulation findings
to real gene drive research debates using specific, accurate references.

MANDATORY STRUCTURE:
1. EXECUTIVE SUMMARY (2-3 sentences — key finding and policy implication)
2. SIMULATION FINDINGS (quantitative summary of what the model showed)
3. ECOLOGICAL RISK ANALYSIS (trophic cascade, frog starvation as unintended consequence,
   ecological dependency of insectivorous predators on target pest populations)
4. CONNECTION TO CURRENT RESEARCH (cite at minimum: Target Malaria project for Anopheles
   gambiae; DARPA Safe Genes program for reversibility research; WHO Guidance Framework for
   Testing of Genetically Modified Mosquitoes (2021); Kevin Esvelt's daisy chain drive concept
   as a more geographically contained alternative to full replacement drives)
5. POLICY CONSIDERATIONS (regulatory gaps, reversibility requirements, Free Prior and Informed
   Consent of affected communities, island vs. continental deployment risk tiers)
6. CONCLUSION

CRITICAL CONSTRAINTS:
- Always distinguish between what the SIMULATION showed and what real ecology has demonstrated.
  Never conflate the two.
- Do not make specific quantitative predictions about real-world outcomes.
- The resistance finding (if it emerged) is particularly important — resistance to CRISPR-based
  gene drives has been observed in laboratory populations.
- Be rigorous and honest about the simulation's limitations: it is a toy model, not a validated
  ecological model.
- Total length: 550-750 words.
"""


def generate_brief(result: "SimulationResult") -> str:
    """Call Claude Haiku and return a formatted policy brief."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set the environment variable to generate a policy brief."
        )

    import anthropic

    resistance_line = ""
    if result.resistance_tick is not None:
        resistance_line = (
            f"\n- Resistance mutation first detected at tick {result.resistance_tick} "
            f"({result.resistance_tick - result.gene_drive_release_tick} ticks after drive release)"
        )

    user_prompt = f"""\
An agent-based gene drive ecosystem simulation has completed. Here are the results:

SIMULATION PARAMETERS:
- Grid: {result.config['width']} x {result.config['height']} units
- Initial mosquito population: {result.config['n_mosquitoes']}
- Initial frog (predator) population: {result.config['n_frogs']}
- Breeding swamps: {result.config['n_swamps']} (spawn rate: {result.config['swamp_spawn_rate']}/tick)
- Gene-drive mosquitoes released at tick {result.gene_drive_release_tick} \
(n={result.config['n_gene_drive']})
- Drive mechanic: 100% of gene-drive carrier offspring are sterile (homing endonuclease model)
- Resistance mutation probability per birth: {result.config['resistance_prob']}
- Total simulation length: {len(result.history)} ticks

POPULATION OUTCOMES:
- Peak mosquito population (pre-drive): {result.peak_mosquitoes}
- Mosquito population minimum after drive: {result.min_mosquitoes_post_drive}
- Final mosquito population: {result.final_mosquitoes}
- Mosquito population reached zero: {result.mosquito_extinction}
- Peak frog population: {result.peak_frogs}
- Frog population minimum after drive: {result.min_frogs_post_drive}
- Final frog population: {result.final_frogs}
- Frog population reached zero: {result.frog_extinction}
- Resistance mutation emerged: {result.resistance_emerged}{resistance_line}

Write a policy brief analyzing these simulation results and connecting them to real gene drive \
research. Focus especially on the trophic cascade (frog starvation as an unintended consequence \
of mosquito population collapse), what resistance emergence implies for drive longevity, and \
what the simulation suggests about the need for ecosystem-level modeling before field deployment.
"""

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return msg.content[0].text.strip()
