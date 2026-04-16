from ..models import NutrientTarget
from ..schemas import Purpose, Species


def get_nutrient_targets(
    species: Species, purpose: Purpose, body_weight_kg: float, milk_yield_lpd: float = 0.0
) -> NutrientTarget:
    # Base dry matter intake as percentage of live weight.
    dm_rate = {
        Species.cattle: 0.030,
        Species.buffalo: 0.028,
        Species.goat: 0.045,
        Species.sheep: 0.040,
        Species.poultry: 0.050,
    }[species]

    base_dm = body_weight_kg * dm_rate
    energy_base = {
        Species.cattle: 0.08,
        Species.buffalo: 0.08,
        Species.goat: 0.11,
        Species.sheep: 0.10,
        Species.poultry: 0.27,
    }[species]

    cp_base = {
        Species.cattle: 0.12,
        Species.buffalo: 0.12,
        Species.goat: 0.16,
        Species.sheep: 0.16,
        Species.poultry: 0.20,
    }[species]

    if purpose == Purpose.dairy:
        dry_matter_kg = max(base_dm, body_weight_kg * 0.032)
        energy_mj = body_weight_kg * energy_base + milk_yield_lpd * 4.5
        crude_protein_pct = 0.14
        calcium_pct = 0.006
        phosphorus_pct = 0.004
        fiber_pct = 0.18
        notes = "Dairy target uses milk production plus maintenance requirements."
    elif purpose == Purpose.growth:
        dry_matter_kg = max(base_dm, body_weight_kg * 0.035)
        energy_mj = body_weight_kg * (energy_base + 0.02)
        crude_protein_pct = min(cp_base + 0.04, 0.18)
        calcium_pct = 0.008
        phosphorus_pct = 0.005
        fiber_pct = 0.15
        notes = "Growth target supports added tissue deposition."
    elif purpose == Purpose.meat:
        dry_matter_kg = max(base_dm, body_weight_kg * 0.032)
        energy_mj = body_weight_kg * (energy_base + 0.012)
        crude_protein_pct = min(cp_base + 0.03, 0.16)
        calcium_pct = 0.006
        phosphorus_pct = 0.004
        fiber_pct = 0.12
        notes = "Meat/fattening target focuses on cost-efficient energy."
    elif purpose == Purpose.maintenance:
        dry_matter_kg = base_dm
        energy_mj = body_weight_kg * energy_base
        crude_protein_pct = cp_base
        calcium_pct = 0.005
        phosphorus_pct = 0.003
        fiber_pct = 0.20
        notes = "Maintenance target is for weight preservation."
    elif purpose == Purpose.layer:
        dry_matter_kg = max(base_dm, body_weight_kg * 0.045)
        energy_mj = body_weight_kg * 0.29
        crude_protein_pct = 0.18
        calcium_pct = 0.035
        phosphorus_pct = 0.004
        fiber_pct = 0.04
        notes = "Layer poultry target supports egg production."
    elif purpose == Purpose.broiler:
        dry_matter_kg = max(base_dm, body_weight_kg * 0.050)
        energy_mj = body_weight_kg * 0.32
        crude_protein_pct = 0.22
        calcium_pct = 0.010
        phosphorus_pct = 0.005
        fiber_pct = 0.03
        notes = "Broiler poultry target supports rapid growth."
    else:
        dry_matter_kg = base_dm
        energy_mj = body_weight_kg * energy_base
        crude_protein_pct = cp_base
        calcium_pct = 0.005
        phosphorus_pct = 0.003
        fiber_pct = 0.18
        notes = "Default target from maintenance guidance."

    return NutrientTarget(
        dry_matter_kg=round(dry_matter_kg, 2),
        crude_protein_pct=round(crude_protein_pct, 3),
        energy_mj=round(energy_mj, 1),
        calcium_pct=round(calcium_pct, 4),
        phosphorus_pct=round(phosphorus_pct, 4),
        fiber_pct=round(fiber_pct, 3),
        notes=notes,
    )
