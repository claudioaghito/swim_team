"""Import/export in Excel del piano di allenamento a fasi (vedi piani_allenamento.py).

Il modello ha una riga per ogni "serie" (non per fase): le colonne di fase
(Tipo, Nome, Durata, Volume, Sottotitolo, Nota) vanno compilate solo sulla prima riga
di ogni fase e vengono ereditate dalle righe successive finche' non cambiano; lo stesso
vale per "Ripetizioni blocco", che raggruppa le righe consecutive in un unico blocco.
"""
import io

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from piani_allenamento import FASI_TIPI, FASI_TIPI_NOMI

FOGLIO_DATI = "Allenamento"

INTESTAZIONI = [
    "Tipo fase", "Nome fase", "Durata fase (min)", "Volume fase (m)",
    "Sottotitolo fase", "Nota fase", "Ripetizioni blocco",
    "Serie", "Esercizio", "Recupero", "Ripartenza",
]

_NOMI_TIPO_LOWER = {nome.strip().lower(): codice for codice, nome, _ in FASI_TIPI}

_ISTRUZIONI = [
    "Come compilare il modello",
    "",
    "Ogni riga del foglio \"Allenamento\" rappresenta una serie, non una fase intera: "
    "una fase con piu' serie occupa piu' righe.",
    "",
    "Tipo fase: scegli dal menu a tendina (Riscaldamento, Tecnica / Esercizi, Attivazione, "
    "Lavoro principale, Defaticamento, Altro). Compilalo solo sulla prima riga della fase: "
    "lascialo vuoto nelle righe successive della stessa fase, viene ereditato automaticamente.",
    "",
    "Nome fase: nome mostrato in allenamento (es. \"Riscaldamento\"). Se lo lasci vuoto viene "
    "usato il nome del tipo scelto.",
    "",
    "Durata fase (min), Volume fase (m), Sottotitolo fase, Nota fase: facoltativi, vanno "
    "indicati solo sulla prima riga della fase.",
    "",
    "Ripetizioni blocco: scrivi \"x2\", \"x3\", ecc. se un gruppo di serie consecutive va "
    "ripetuto piu' volte di seguito; lascialo vuoto per una serie singola. Le righe consecutive "
    "con lo stesso valore in questa colonna vengono raggruppate nello stesso blocco.",
    "Attenzione: se due blocchi diversi della stessa fase hanno per caso la stessa etichetta "
    "(es. entrambi \"x2\"), verranno uniti in un unico blocco. Per tenerli separati usa "
    "un'etichetta leggermente diversa o inserisci fra loro una riga con ripetizione vuota.",
    "",
    "Serie, Esercizio, Recupero, Ripartenza: testo libero, scrivi come vuoi che compaia "
    "nell'allenamento (es. \"4x50 m\", \"15\\\"\", \"1'10\\\"\").",
    "",
    "Guarda il foglio \"Esempio\" per un caso gia' compilato.",
    "",
    "Una volta compilato, salva il file e caricalo nella pagina \"Nuovo allenamento\" con il "
    "pulsante \"Importa da Excel\": il piano importato viene caricato nel builder, dove puoi "
    "ancora correggerlo prima di salvare l'allenamento.",
]

_ESEMPIO_RIGHE = [
    ["Riscaldamento", "Riscaldamento", 10, 400, "", "", "", "8x50 m", "Libero facile, respirazione 3", "20\"", ""],
    ["", "", "", "", "", "", "", "4x50 m", "Dorso", "15\"", ""],
    ["Lavoro principale", "Serie principale", 25, 800, "Ripetute a ritmo gara", "", "x2",
     "4x100 SL", "Ritmo gara, spinta sui virata", "30\"", "1'40\""],
    ["", "", "", "", "", "", "x2", "50 SL", "Veloce", "20\"", ""],
    ["", "", "", "", "", "", "", "200 m", "Nuoto libero facile di recupero", "", ""],
]


def genera_template_excel():
    """Crea il modello .xlsx da distribuire agli operatori. Ritorna un BytesIO pronto per send_file."""
    wb = openpyxl.Workbook()

    ws = wb.active
    ws.title = FOGLIO_DATI
    ws.append(INTESTAZIONI)
    for cella in ws[1]:
        cella.font = Font(bold=True, color="FFFFFF")
        cella.fill = PatternFill("solid", fgColor="2AACC8")
        cella.alignment = Alignment(wrap_text=True, vertical="center")
    for lettera, larghezza in zip("ABCDEFGHIJK", [18, 20, 14, 14, 26, 26, 16, 18, 40, 12, 14]):
        ws.column_dimensions[lettera].width = larghezza
    ws.freeze_panes = "A2"

    nomi_tipi = [nome for _, nome, _ in FASI_TIPI]
    dv = DataValidation(
        type="list", formula1='"' + ",".join(nomi_tipi) + '"',
        allow_blank=True, showErrorMessage=True,
    )
    dv.error = "Scegli uno dei tipi di fase dall'elenco."
    dv.errorTitle = "Tipo fase non valido"
    ws.add_data_validation(dv)
    dv.add("A2:A500")

    istruzioni = wb.create_sheet("Istruzioni")
    istruzioni.column_dimensions["A"].width = 110
    for testo in _ISTRUZIONI:
        istruzioni.append([testo])
    istruzioni["A1"].font = Font(bold=True, size=13)
    for cella in istruzioni["A"]:
        cella.alignment = Alignment(wrap_text=True, vertical="top")

    esempio = wb.create_sheet("Esempio")
    esempio.append(INTESTAZIONI)
    for cella in esempio[1]:
        cella.font = Font(bold=True)
    for riga in _ESEMPIO_RIGHE:
        esempio.append(riga)
    for lettera, larghezza in zip("ABCDEFGHIJK", [18, 20, 14, 14, 26, 26, 16, 18, 40, 12, 14]):
        esempio.column_dimensions[lettera].width = larghezza

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _testo(cella):
    valore = cella.value if cella is not None else None
    return str(valore).strip() if valore is not None else ""


def _intero(cella):
    valore = cella.value if cella is not None else None
    if valore is None or valore == "":
        return None
    try:
        return int(valore)
    except (TypeError, ValueError):
        return None


def leggi_piano_da_excel(file_stream):
    """Legge un file .xlsx compilato secondo il modello e lo converte nella stessa forma
    prodotta dal builder JS (vedi piano_allenamento.js / _pulisci_piano in admin.py):
    [{tipo, nome, durata_min, metri, sottotitolo, nota, blocchi:[{ripetizioni, righe:[...]}]}].
    Ritorna (fasi, errori): 'errori' elenca le righe scartate, 'fasi' e' comunque popolato
    con tutto cio' che si e' potuto leggere correttamente."""
    try:
        wb = openpyxl.load_workbook(file_stream, data_only=True, read_only=True)
    except Exception:
        return [], ["Il file non e' un foglio Excel (.xlsx) valido."]

    ws = wb[FOGLIO_DATI] if FOGLIO_DATI in wb.sheetnames else wb.worksheets[0]

    fasi = []
    errori = []
    fase_corrente = None
    blocco_corrente = None
    chiave_blocco_corrente = None

    for numero, riga in enumerate(ws.iter_rows(min_row=2, max_col=11), start=2):
        celle = list(riga) + [None] * (11 - len(riga))
        tipo_raw = _testo(celle[0])
        nome_raw = _testo(celle[1])
        durata = _intero(celle[2])
        metri = _intero(celle[3])
        sottotitolo = _testo(celle[4])
        nota = _testo(celle[5])
        ripetizioni = _testo(celle[6])
        serie = _testo(celle[7])
        esercizio = _testo(celle[8])
        recupero = _testo(celle[9])
        ripartenza = _testo(celle[10])

        if not any([tipo_raw, nome_raw, durata, metri, sottotitolo, nota, ripetizioni,
                    serie, esercizio, recupero, ripartenza]):
            continue  # riga completamente vuota

        if not (serie or esercizio or recupero or ripartenza):
            errori.append(f"Riga {numero}: nessuna serie indicata, riga ignorata.")
            continue

        if tipo_raw:
            tipo_codice = _NOMI_TIPO_LOWER.get(tipo_raw.lower())
            if tipo_codice is None:
                errori.append(f"Riga {numero}: tipo fase \"{tipo_raw}\" non riconosciuto, riga ignorata.")
                continue
        elif fase_corrente is not None:
            tipo_codice = fase_corrente["tipo"]
        else:
            errori.append(f"Riga {numero}: manca il tipo fase e non c'e' una fase precedente da cui ereditarlo, riga ignorata.")
            continue

        if nome_raw:
            nome = nome_raw
        elif tipo_raw:
            nome = FASI_TIPI_NOMI.get(tipo_codice, "")
        else:
            nome = fase_corrente["nome"] if fase_corrente else FASI_TIPI_NOMI.get(tipo_codice, "")

        nuova_fase = fase_corrente is None or tipo_codice != fase_corrente["tipo"] or nome != fase_corrente["nome"]
        if nuova_fase:
            fase_corrente = {
                "tipo": tipo_codice, "nome": nome,
                "durata_min": None, "metri": None, "sottotitolo": "", "nota": "",
                "blocchi": [],
            }
            fasi.append(fase_corrente)
            blocco_corrente = None
            chiave_blocco_corrente = None

        if durata is not None and fase_corrente["durata_min"] is None:
            fase_corrente["durata_min"] = durata
        if metri is not None and fase_corrente["metri"] is None:
            fase_corrente["metri"] = metri
        if sottotitolo and not fase_corrente["sottotitolo"]:
            fase_corrente["sottotitolo"] = sottotitolo
        if nota and not fase_corrente["nota"]:
            fase_corrente["nota"] = nota

        rip_norm = "" if ripetizioni in ("-", "—") else ripetizioni
        if blocco_corrente is None or rip_norm != chiave_blocco_corrente:
            blocco_corrente = {"ripetizioni": rip_norm, "righe": []}
            fase_corrente["blocchi"].append(blocco_corrente)
            chiave_blocco_corrente = rip_norm

        blocco_corrente["righe"].append({
            "serie": serie, "esercizio": esercizio, "recupero": recupero, "ripartenza": ripartenza,
        })

    if not fasi and not errori:
        errori.append("Il file non contiene righe compilate.")

    return fasi, errori
