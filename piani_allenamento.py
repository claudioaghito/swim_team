"""Tipi di fase per il piano di allenamento strutturato (vedi Allenamento.piano in models.py).
Ogni tipo fissa icona e colore della card; il nome mostrato resta modificabile in fase di creazione."""

FASI_TIPI = [
    ("riscaldamento", "Riscaldamento", "#2AACC8"),
    ("tecnica", "Tecnica / Esercizi", "#6C5CE7"),
    ("attivazione", "Attivazione", "#E8A400"),
    ("principale", "Lavoro principale", "#D9481E"),
    ("defaticamento", "Defaticamento", "#3E7FBF"),
    ("altro", "Altro", "#5F6B76"),
]

FASI_TIPI_CODICI = {codice for codice, _, _ in FASI_TIPI}
FASI_TIPI_NOMI = {codice: nome for codice, nome, _ in FASI_TIPI}
FASI_TIPI_COLORE = {codice: colore for codice, _, colore in FASI_TIPI}


def fase_icona(tipo):
    return f"fase-{tipo}" if tipo in FASI_TIPI_CODICI else "fase-altro"


def fase_colore(tipo):
    return FASI_TIPI_COLORE.get(tipo, FASI_TIPI_COLORE["altro"])


def normalizza_fasi(fasi):
    """Garantisce che ogni fase esponga 'blocchi': [{ripetizioni, righe:[{serie,esercizio,
    recupero,ripartenza}]}], convertendo al volo il vecchio formato con 'righe' piatte
    (una per serie, con rip_blocco individuale) raggruppando le righe consecutive che
    condividono lo stesso rip_blocco. Permette di leggere dati salvati prima di questa
    struttura senza bisogno di migrare il database."""
    normalizzate = []
    for fase in fasi:
        if not isinstance(fase, dict):
            continue
        if "blocchi" in fase:
            normalizzate.append(fase)
            continue

        blocchi = []
        corrente = None
        for riga in fase.get("righe") or []:
            if not isinstance(riga, dict):
                continue
            rip = (riga.get("rip_blocco") or "").strip()
            rip = "" if rip in ("-", "—") else rip
            if corrente is None or corrente["ripetizioni"] != rip:
                corrente = {"ripetizioni": rip, "righe": []}
                blocchi.append(corrente)
            corrente["righe"].append({
                "serie": riga.get("serie", ""),
                "esercizio": riga.get("esercizio", ""),
                "recupero": riga.get("recupero", ""),
                "ripartenza": riga.get("ripartenza", ""),
            })

        nuova = dict(fase)
        nuova.pop("righe", None)
        nuova["blocchi"] = blocchi
        normalizzate.append(nuova)
    return normalizzate
