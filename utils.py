"""Funzioni di supporto per la gestione dei tempi (minuti/secondi), condivise
tra admin.py e athlete.py."""


def tempo_a_secondi(testo):
    """Converte un tempo tipo '01:02.35' o '62.35' in secondi (float). None se vuoto/non valido."""
    testo = (testo or "").strip().replace(",", ".")
    if not testo:
        return None
    try:
        if ":" in testo:
            minuti, resto = testo.split(":", 1)
            return int(minuti) * 60 + float(resto)
        return float(testo)
    except ValueError:
        return None


def secondi_a_tempo(secondi):
    """Converte secondi (float) nel formato mm:ss.cc, es. 62.35 -> '01:02.35'."""
    minuti = int(secondi // 60)
    resto = secondi - minuti * 60
    return f"{minuti:02d}:{resto:05.2f}"


def min_sec_a_secondi(minuti_raw, secondi_raw):
    """Combina i campi separati minuti e secondi (stringhe da form) in secondi totali.
    None se entrambi vuoti o se il contenuto non e' un numero valido: il tempo resta
    facoltativo, niente viene forzato quando non serve (es. strategia eta' minima fascia)."""
    minuti_raw = (minuti_raw or "").strip()
    secondi_raw = (secondi_raw or "").strip().replace(",", ".")
    if not minuti_raw and not secondi_raw:
        return None
    try:
        minuti = int(minuti_raw) if minuti_raw else 0
        secondi = float(secondi_raw) if secondi_raw else 0.0
        return minuti * 60 + secondi
    except ValueError:
        return None


def secondi_a_min_sec_str(secondi):
    """Divide i secondi totali in (minuti, secondi) come stringhe, per precompilare
    due campi separati. ('', '') se non disponibile."""
    if secondi is None:
        return "", ""
    minuti = int(secondi // 60)
    resto = round(secondi - minuti * 60, 2)
    secondi_str = str(int(resto)) if resto == int(resto) else f"{resto:.2f}"
    return str(minuti), secondi_str


def tempo_stringa_a_min_sec_str(testo):
    """Converte un tempo salvato come stringa (es. '01:02.35') in (minuti, secondi)
    come stringhe pronte per precompilare due campi separati."""
    return secondi_a_min_sec_str(tempo_a_secondi(testo))
