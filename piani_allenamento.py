"""Tipi di fase per il piano di allenamento strutturato (vedi Allenamento.piano in models.py).
Ogni tipo fissa icona e colore della card; il nome mostrato resta modificabile in fase di creazione."""

import re

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


def _valore_serie(testo):
    """Prodotto dei numeri in una cella 'Serie' separati da 'x'/'X' (es. '4x50 m' => 200).
    Rispecchia parseValoreSerie() in static/js/piano_allenamento.js."""
    if not testo:
        return 0
    pulito = re.sub(r"\s+", "", str(testo))
    numeri = []
    for parte in re.split(r"[xX]", pulito):
        m = re.search(r"\d+(?:[.,]\d+)?", parte)
        if m:
            numeri.append(float(m.group(0).replace(",", ".")))
    if not numeri:
        return 0
    totale = 1.0
    for n in numeri:
        totale *= n
    return totale


def _moltiplicatore_blocco(testo):
    """Moltiplicatore di un blocco (es. 'x2' => 2); 1 se vuoto o non numerico.
    Rispecchia parseMoltiplicatoreBlocco() in static/js/piano_allenamento.js."""
    if not testo:
        return 1
    m = re.search(r"\d+(?:[.,]\d+)?", re.sub(r"\s+", "", str(testo)))
    if not m:
        return 1
    n = float(m.group(0).replace(",", "."))
    return n if n > 0 else 1


def calcola_volume_fase(fase):
    """Volume (metri) di una fase calcolato dai suoi blocchi, usato come fallback quando
    il piano e' stato salvato prima del calcolo automatico introdotto nel builder (il
    campo 'metri' non esiste ancora per quelle fasi). Stessa logica di
    calcolaVolumeFase() in static/js/piano_allenamento.js."""
    totale = 0.0
    for blocco in fase.get("blocchi") or []:
        moltiplicatore = _moltiplicatore_blocco(blocco.get("ripetizioni"))
        somma_blocco = sum(_valore_serie(riga.get("serie")) for riga in blocco.get("righe") or [])
        totale += somma_blocco * moltiplicatore
    return int(totale) if totale else 0


def normalizza_fasi(fasi):
    """Garantisce che ogni fase esponga 'blocchi': [{ripetizioni, righe:[{serie,esercizio,
    recupero,ripartenza}]}], convertendo al volo il vecchio formato con 'righe' piatte
    (una per serie, con rip_blocco individuale) raggruppando le righe consecutive che
    condividono lo stesso rip_blocco. Permette di leggere dati salvati prima di questa
    struttura senza bisogno di migrare il database.

    Calcola anche 'metri' dai blocchi quando mancante, per i piani salvati prima
    dell'introduzione del calcolo automatico del volume."""
    normalizzate = []
    for fase in fasi:
        if not isinstance(fase, dict):
            continue
        if "blocchi" in fase:
            nuova = dict(fase)
        else:
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

        if not nuova.get("metri"):
            volume = calcola_volume_fase(nuova)
            if volume:
                nuova["metri"] = volume

        normalizzate.append(nuova)
    return normalizzate
