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
