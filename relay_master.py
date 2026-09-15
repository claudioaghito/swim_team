"""Logica di selezione della formazione ottimale per le staffette Master FIN.

Le soglie in RELAY_BRACKETS sono un default plausibile: vanno confermate
contro il regolamento ufficiale della specifica manifestazione, perche'
possono variare tra FIN nazionale, regionale e Supermaster.

Per le gare individuali FIN si usa un riferimento di eta' leggermente
diverso da quello delle staffette (vedi User.categoria_master in
models.py); questo modulo copre solo la logica delle staffette.

Assunzione da confermare: per la staffetta mista (M/F) si assume una
composizione fissa di 2 uomini + 2 donne, come da prassi FIN piu' comune;
alcuni regolamenti ammettono composizioni diverse.
"""

from dataclasses import dataclass, field
from itertools import combinations, permutations


# Soglie (somma eta' minima/massima) per categoria staffetta Master FIN.
# DEFAULT PLAUSIBILE, DA CONFERMARE per la specifica manifestazione.
RELAY_BRACKETS = {
    "100": (100, 119),
    "120": (120, 159),
    "160": (160, 199),
    "200": (200, 239),
    "240": (240, 279),
    "280": (280, 319),
    "320": (320, 359),
    "360": (360, 399),
    "400": (400, None),  # None = nessun limite superiore
}

STRATEGIE = ("tempo_minimo", "eta_minima_fascia")


@dataclass
class Nuotatore:
    nome: str
    eta: int
    sesso: str = None  # "M" o "F", opzionale: serve solo se si usa tipo_squadra
    tempi: dict = field(default_factory=dict)  # tempo in secondi per prova, es. {"SL": 28.4}


@dataclass
class Formazione:
    frazioni: list  # [(Nuotatore, prova_assegnata), ...] nell'ordine delle prove
    tempo_totale: float
    somma_eta: int

    @property
    def nuotatori(self):
        return [n for n, _ in self.frazioni]


def _composizione_valida(gruppo, tipo_squadra):
    if tipo_squadra is None:
        return True
    if tipo_squadra == "MISTA":
        maschi = sum(1 for n in gruppo if n.sesso == "M")
        femmine = sum(1 for n in gruppo if n.sesso == "F")
        return maschi == 2 and femmine == 2
    return all(n.sesso == tipo_squadra for n in gruppo)


def _migliore_assegnazione(gruppo, prove, richiedi_tempi=True):
    """Tra le permutazioni dei 4 nuotatori sulle prove richieste, trova quella
    con tempo totale minimo (tra quelle con tempi completi su tutte le frazioni).

    Se richiedi_tempi e' True (strategia "tempo_minimo") e nessuna permutazione
    ha tempi completi, ritorna None: senza tempi non si puo' minimizzare nulla.

    Se richiedi_tempi e' False (strategia "eta_minima_fascia", dove il tempo e'
    facoltativo), in assenza di tempi completi ritorna comunque un abbinamento
    nell'ordine dato dei candidati, con tempo_totale a None se non tutte le
    frazioni hanno un tempo inserito."""
    migliore = None
    for ordine in permutations(gruppo):
        tempo_totale = 0.0
        valida = True
        for nuotatore, prova in zip(ordine, prove):
            tempo = nuotatore.tempi.get(prova)
            if tempo is None:
                valida = False
                break
            tempo_totale += tempo
        if not valida:
            continue
        if migliore is None or tempo_totale < migliore[1]:
            frazioni = list(zip(ordine, prove))
            migliore = (frazioni, tempo_totale)

    if migliore is not None or richiedi_tempi:
        return migliore

    frazioni = list(zip(gruppo, prove))
    tempi_presenti = [n.tempi[p] for n, p in frazioni if p in n.tempi]
    tempo_totale = sum(tempi_presenti) if len(tempi_presenti) == len(prove) else None
    return frazioni, tempo_totale


def _categoria_per_somma_eta(somma_eta):
    """Chiave di RELAY_BRACKETS in cui rientra la somma eta' indicata, o None
    se sotto la soglia minima piu' bassa prevista."""
    for categoria, (eta_min, eta_max) in RELAY_BRACKETS.items():
        if somma_eta >= eta_min and (eta_max is None or somma_eta <= eta_max):
            return categoria
    return None


def tutte_le_formazioni_possibili(candidati, prove, tipo_squadra=None, strategia="tempo_minimo"):
    """Genera automaticamente tutte le categorie raggiungibili con i candidati a
    disposizione (non serve indicare a priori una categoria target: le condizioni
    possibili vengono derivate dalle combinazioni reali di eta' e composizione),
    e per ciascuna calcola la formazione migliore secondo la strategia scelta.

    candidati, prove, tipo_squadra, strategia: vedi formazione_migliore_per_categoria_target.

    Ritorna un dict {categoria: Formazione} con solo le categorie per cui esiste
    almeno una formazione valida tra i candidati.
    """
    if strategia not in STRATEGIE:
        raise ValueError(f"Strategia sconosciuta: {strategia}")
    if len(prove) != 4:
        raise ValueError("Una staffetta richiede esattamente 4 prove/frazioni")

    richiedi_tempi = strategia == "tempo_minimo"

    migliori = {}
    for gruppo in combinations(candidati, 4):
        somma_eta = sum(n.eta for n in gruppo)
        categoria = _categoria_per_somma_eta(somma_eta)
        if categoria is None:
            continue
        if not _composizione_valida(gruppo, tipo_squadra):
            continue
        assegnazione = _migliore_assegnazione(gruppo, prove, richiedi_tempi=richiedi_tempi)
        if assegnazione is None:
            continue
        frazioni, tempo_totale = assegnazione
        formazione = Formazione(frazioni, tempo_totale, somma_eta)

        attuale = migliori.get(categoria)
        if attuale is None:
            migliori[categoria] = formazione
        elif strategia == "tempo_minimo":
            if formazione.tempo_totale < attuale.tempo_totale:
                migliori[categoria] = formazione
        else:  # eta_minima_fascia: il tempo e' facoltativo, si sceglie solo per eta'
            eta_min = RELAY_BRACKETS[categoria][0]
            if (formazione.somma_eta - eta_min) < (attuale.somma_eta - eta_min):
                migliori[categoria] = formazione

    return migliori


def formazione_migliore_per_categoria_target(
    candidati,
    categoria_target,
    prove,
    tipo_squadra=None,
    strategia="tempo_minimo",
):
    """Trova la formazione di 4 nuotatori migliore per la categoria target.

    candidati: lista di Nuotatore disponibili.
    categoria_target: chiave di RELAY_BRACKETS (es. "160").
    prove: le 4 prove della staffetta nell'ordine di frazione, es.
        ["SL", "SL", "SL", "SL"] per una 4x100 SL, oppure
        ["DO", "RA", "FA", "SL"] per una 4x100 misti.
    tipo_squadra: None (nessun vincolo, il chiamante ha gia' selezionato un
        gruppo di candidati coerente con il tipo di staffetta), oppure "M",
        "F" o "MISTA" per far applicare qui il vincolo di composizione
        (sulla mista si assume 2+2, vedi nota in cima al modulo).
    strategia:
        - "tempo_minimo": minimizza il tempo totale tra le formazioni che
          rientrano nella fascia d'eta' della categoria target.
        - "eta_minima_fascia": tra le formazioni valide, sceglie quella con
          somma eta' piu' vicina al minimo della fascia, per restare
          "giovani" nella categoria.

    Ritorna una Formazione, oppure None se nessuna combinazione soddisfa
    i vincoli (composizione, fascia d'eta', tempi disponibili per le prove).
    """
    if categoria_target not in RELAY_BRACKETS:
        raise ValueError(f"Categoria sconosciuta: {categoria_target}")
    if strategia not in STRATEGIE:
        raise ValueError(f"Strategia sconosciuta: {strategia}")
    if len(prove) != 4:
        raise ValueError("Una staffetta richiede esattamente 4 prove/frazioni")

    eta_min, eta_max = RELAY_BRACKETS[categoria_target]
    richiedi_tempi = strategia == "tempo_minimo"

    formazioni_valide = []
    for gruppo in combinations(candidati, 4):
        somma_eta = sum(n.eta for n in gruppo)
        if somma_eta < eta_min or (eta_max is not None and somma_eta > eta_max):
            continue
        if not _composizione_valida(gruppo, tipo_squadra):
            continue
        assegnazione = _migliore_assegnazione(gruppo, prove, richiedi_tempi=richiedi_tempi)
        if assegnazione is None:
            continue
        frazioni, tempo_totale = assegnazione
        formazioni_valide.append(Formazione(frazioni, tempo_totale, somma_eta))

    if not formazioni_valide:
        return None

    if strategia == "tempo_minimo":
        return min(formazioni_valide, key=lambda f: f.tempo_totale)
    return min(formazioni_valide, key=lambda f: f.somma_eta - eta_min)
