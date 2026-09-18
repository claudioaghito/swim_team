"""Struttura fissa dei record societari: stili, distanze e categorie master,
nello stesso ordine della tabella storica del club (vedi import_record_societari.py)."""

STILI_RECORD = [
    ("SL", "Stile Libero", [50, 100, 200, 400, 800, 1500]),
    ("DF", "Delfino", [50, 100, 200]),
    ("DO", "Dorso", [50, 100, 200]),
    ("RA", "Rana", [50, 100, 200]),
    ("MX", "Misti", [100, 200, 400]),
]

STILI_CODICI = {codice for codice, _, _ in STILI_RECORD}
STILI_NOMI = {codice: nome for codice, nome, _ in STILI_RECORD}
DISTANZE_PER_STILE = {codice: distanze for codice, _, distanze in STILI_RECORD}

CATEGORIE_RECORD = [
    "M25", "M30", "M35", "M40", "M45", "M50", "M55", "M60", "M65", "M70", "M75", "M80", "M85", "M90",
]


def griglia_record(records):
    """Organizza una lista di RecordSocietario in una struttura pronta per il template:
    una sezione per stile, con righe per categoria e celle (distanza, record_o_None)."""
    indice = {(r.stile, r.categoria, r.distanza): r for r in records}
    griglia = []
    for codice, etichetta, distanze in STILI_RECORD:
        righe = []
        for categoria in CATEGORIE_RECORD:
            celle = [(d, indice.get((codice, categoria, d))) for d in distanze]
            righe.append((categoria, celle))
        griglia.append({"codice": codice, "etichetta": etichetta, "distanze": distanze, "righe": righe})
    return griglia
