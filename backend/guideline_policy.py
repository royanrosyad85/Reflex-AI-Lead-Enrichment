from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class GuidelinePolicyEngine:
    raw_text: str

    @classmethod
    def from_file(cls, path: str) -> "GuidelinePolicyEngine":
        return cls(raw_text=Path(path).read_text(encoding="utf-8"))


ALLOWED_POLICIES = [
    "MV4", "MV2", "PA", "Cargo", "Heavy Equipment", "Marine", "Travel", "Properti", "TPL"
]


def _contains_any(text: str, keywords: List[str]) -> bool:
    lower = text.lower()
    return any(k in lower for k in keywords)


def infer_potensi_polis(
    sektor: str,
    short_description: str,
    jumlah_karyawan: str,
    kantor_cabang: str,
) -> str:
    """Infer insurance policy potential based on guideline rules.
    
    Rules derived from guidline.md:
    - MV4: company has many operational cars (not high-risk claim)
    - MV2: company has many operational motorcycles
    - PA: companies with many employees and heavy work (manufacturing, construction)
    - Cargo: logistics, inter-city/island trade, export-import, distribution
    - Heavy Equipment: excavator, loader, forklift, crane, construction equipment
    - Marine: logistics sector, industrial ships, port operations
    - Travel: companies with routine employee travel
    - Properti: companies with office buildings, factories, other buildings
    """
    text = f"{sektor} {short_description} {jumlah_karyawan} {kantor_cabang}".lower()
    picks: List[str] = []

    # Cargo + Marine: logistics, export-import, distribution
    if _contains_any(text, ["logistik", "logistics", "ekspor", "impor", "export", "import", 
                            "distribusi", "distribution", "cargo", "pengiriman", "freight",
                            "perdagangan antar", "antar pulau", "antarpulau"]):
        picks.extend(["Cargo", "Marine"])

    # Construction: MV4 + PA + Heavy Equipment
    if _contains_any(text, ["konstruksi", "kontruksi", "construction", 
                            "excavator", "loader", "forklift", "crane", 
                            "alat berat", "heavy equipment", "peralatan konstruksi"]):
        picks.extend(["MV4", "PA", "Heavy Equipment"])

    # Manufacturing / heavy work: PA + Properti
    if _contains_any(text, ["manufaktur", "manufacturing", "pabrik", "factory",
                            "pekerjaan berat", "industri"]):
        if "PA" not in picks:
            picks.append("PA")
        picks.append("Properti")

    # Many employees (general PA trigger for employee benefit)
    if _contains_any(text, ["karyawan", "employee", "pegawai", "pekerja"]):
        if "PA" not in picks:
            picks.append("PA")

    # Motor vehicles (operational fleet)
    if _contains_any(text, ["armada", "mobil operasional", "kendaraan operasional", "fleet"]):
        if "MV4" not in picks:
            picks.append("MV4")

    # Property: buildings, factories
    if _contains_any(text, ["gedung", "bangunan", "building", "kantor pusat", "gudang", "warehouse"]):
        if "Properti" not in picks:
            picks.append("Properti")

    # Travel
    if _contains_any(text, ["perjalanan dinas", "travel", "perjalanan rutin", "business trip"]):
        picks.append("Travel")

    # Motorcycles
    if _contains_any(text, ["motor operasional", "motorcycle", "sepeda motor"]):
        picks.append("MV2")

    # Marine specific (port, ships)
    if _contains_any(text, ["pelabuhan", "port", "kapal", "ship", "vessel", "maritim", "maritime"]):
        if "Marine" not in picks:
            picks.append("Marine")

    # Deduplicate while preserving order
    ordered_unique: List[str] = []
    for p in picks:
        if p in ALLOWED_POLICIES and p not in ordered_unique:
            ordered_unique.append(p)

    return ", ".join(ordered_unique) if ordered_unique else "Tidak Tersedia"
