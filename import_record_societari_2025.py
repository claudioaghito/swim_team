# -*- coding: utf-8 -*-
"""Importa una tantum i record societari aggiornati a fine stagione 2024/2025
(PDF "Record_Societari-<sesso> vasca da <25|50>m.pdf") nel database.

A differenza di import_record_societari.py (che trascriveva i dati a mano in un
dizionario Python), qui il testo di ogni riga del PDF e' incollato cosi' com'e'
(stessa sequenza "Cat Tempo Nome Data" ripetuta una volta per distanza) e un
parser a codice lo trasforma in record: piu' sicuro su ~280 righe di dati, perche'
evita di dover assegnare a mano ogni valore alla colonna/distanza giusta (compito
non banale quando una riga ha piu' celle vuote di fila, vedi _dividi_riga).

Per la vasca da 50m molte celle hanno il nome della manifestazione invece della
data esatta (es. "Mondiali 2012", "italiani 2018"): va nel campo RecordSocietario.evento
(vedi models.py) e si mostra al posto della data.

Rilanciabile in sicurezza: aggiorna (upsert) i record gia' presenti invece di
duplicarli, e non tocca i record che non compaiono in nessuna riga qui sotto.

Uso: python import_record_societari_2025.py
"""
import re
from datetime import datetime

from app import create_app
from extensions import db
from models import RecordSocietario
from records import CATEGORIE_RECORD, DISTANZE_PER_STILE

RIGA_RE = re.compile(r'M\d{2}(.*?)(?=\s*M\d{2}|$)')
DATA_RE = re.compile(r'\d{2}/\d{2}/\d{4}')
EVENTO_RE = re.compile(r'[A-Za-z]+\s+\d{4}')


def _dividi_riga(riga, n_colonne):
    """Divide una riga "M25 ... M25 ... M25 ..." nelle n_colonne celle (una per
    distanza), usando le ripetizioni di "M\\d\\d" come separatori: e' l'unico modo
    affidabile di assegnare il contenuto alla colonna giusta quando ci sono piu'
    celle vuote di fila (una cella vuota e' comunque preceduta dal suo "M25")."""
    celle = RIGA_RE.findall(riga)
    if len(celle) != n_colonne:
        raise ValueError(f"attese {n_colonne} colonne, trovate {len(celle)}: {riga!r}")
    return celle


def _parsa_cella(testo):
    token = testo.split()
    if not token:
        return None  # cella vuota: nessun record per quella distanza/categoria
    tempo = token[0]
    resto = token[1:]
    if not resto:
        raise ValueError(f"tempo senza nome: {testo!r}")
    ultimo = resto[-1]
    if DATA_RE.fullmatch(ultimo):
        nome = " ".join(resto[:-1])
        return tempo, nome, datetime.strptime(ultimo, "%d/%m/%Y").date(), None
    if len(resto) >= 2 and EVENTO_RE.fullmatch(f"{resto[-2]} {resto[-1]}"):
        nome = " ".join(resto[:-2])
        return tempo, nome, None, f"{resto[-2].capitalize()} {resto[-1]}"
    raise ValueError(f"data/evento non riconosciuti in fondo alla cella: {testo!r}")


def _righe(testo, n_attese=14):
    righe = [r for r in testo.strip("\n").split("\n") if r.strip()]
    if len(righe) != n_attese:
        raise ValueError(f"attese {n_attese} righe, trovate {len(righe)}")
    return righe


# ---------------------------------------------------------------------------
# Testo incollato cosi' com'e' dai 4 PDF (una riga per categoria, stesso ordine
# di CATEGORIE_RECORD in records.py: M25..M90), raggruppato per sesso/vasca/stile
# nello stesso ordine di STILI_RECORD (SL, DF, DO, RA, MX).
# ---------------------------------------------------------------------------

DONNE_25_SL = _righe("""
M25 28"28 Frattini Francesca 26/01/2013 M25 1'01"28 Anfossi Giulia 15/04/2012 M25 2'13"66 Lugano Diletta 03/11/2013 M25 4'44"10 Lugano Diletta 24/03/2012 M25 10'16"40 Scaramel Cristiana 10/01/2004 M25 19'30"99 Valdata Carlotta 11/02/2018
M30 27"68 Dematti Delia 27/04/2003 M30 1'01"83 Dematti Delia 06/04/2003 M30 2'16"04 Lugano Diletta 30/03/2014 M30 4'49"64 Lugano Valentina 26/10/2013 M30 9'58"99 Lugano Diletta 15/11/2015 M30 19'34"10 Lugano Valentina 04/03/2012
M35 27"47 Dematti Delia 25/10/2003 M35 1'00"69 Dematti Delia 04/04/2004 M35 2'17"07 Dematti Delia 30/04/2006 M35 4'50"90 Dematti Delia 12/02/2006 M35 10'09"29 Lugano Valentina 11/02/2018 M35 19'35"02 Lugano Valentina 22/02/2015
M40 28"56 Dematti Delia 13/12/2009 M40 1'02"85 Vitaloni Sabina 10/03/2013 M40 2'20"80 Lugano Valentina 19/01/2020 M40 4'51"93 Lugano Valentina 11/02/2023 M40 9'59"82 Lugano Valentina 17/02/2024 M40 19'23"25 Lugano Valentina 12/02/2022
M45 28"67 Vitaloni Sabina 21/02/2015 M45 1'03"57 Vitaloni Sabina 23/04/2017 M45 2'22"50 Lugano Valentina 12/01/2025 M45 4'55"35 Lugano Valentina 08/02/2025 M45 10'09"30 Lugano Valentina 19/01/2025 M45 19'35"50 Lugano Valentina 08/03/2025
M50 29"43 Vitaloni Sabina 07/04/2024 M50 1'05"23 Vitaloni Sabina 05/03/2023 M50 2'34"05 Dematti Delia 22/01/2023 M50 6'17"37 Rolando Ida 13/12/2009 M50 11'06"33 Tava Francesca 30/03/2025 M50 21'43"60 Tava Francesca 08/03/2025
M55 29"95 Vitaloni Sabina 06/04/2025 M55 1'24"49 Rolando Ida 17/04/2011 M55 3'03"43 Rolando Ida 13/03/2011 M55 6'27"62 Rolando Ida 25/10/2014 M55 13'27"09 Rolando Ida 21/02/2015 M55
M60 42"53 Rolando Ida 20/01/2019 M60 1'29"83 Rolando Ida 02/12/2018 M60 3'22"93 Rolando Ida 20/01/2019 M60 6'36"36 Rolando Ida 11/12/2016 M60 13'25"11 Rolando Ida 19/02/2017 M60
M65 43"89 Rolando Ida 19/12/2021 M65 1'36"90 Valloni Susanna 27/02/2021 M65 4'18"04 Alice Irene 03/12/2006 M65 6'56"51 Rolando Ida 19/12/2021 M65 14'29"90 Rolando Ida 08/03/2025 M65 27'40"36 Rolando Ida 08/02/2025
M70 52"87 Alice Irene 28/10/2007 M70 2'01"73 Alice Irene 28/10/2007 M70 4'14"81 Alice Irene 17/11/2007 M70 8'54"09 Alice Irene 23/12/2007 M70 M70
M75 1'04"03 Bois Gabriella 22/12/2019 M75 M75 M75 10'07"00 Bois Gabriella 22/12/2019 M75 20'06"08 Bois Gabriella 15/02/2020 M75
M80 M80 M80 M80 M80 M80
M85 M85 M85 M85 M85 M85
M90 M90 M90 M90 M90 M90
""")

DONNE_25_DF = _righe("""
M25 29"69 Anfossi Giulia 29/01/2012 M25 1'05"26 Anfossi Giulia 26/02/2012 M25 2'48"42 Valdata Carlotta 22/04/2018
M30 31"10 Lugano Diletta 29/11/2015 M30 1'11"30 Colorio Barbara 12/03/2006 M30 2'39"66 Colombo Silvia 25/03/2006
M35 30"46 Dematti Delia 21/12/2003 M35 1'21"30 Lugano Valentina 08/02/2019 M35 3'00"84 Lugano Valentina 23/12/2018
M40 31"62 Vitaloni Sabina 13/01/2013 M40 1'22"62 Lugano Valentina 10/04/2022 M40 2'58"80 Lugano Valentina 19/03/2022
M45 31"53 Vitaloni Sabina 10/04/2016 M45 1'34"15 Tava Francesca 10/11/2024 M45 3'30"48 Tava Francesca 17/11/2024
M50 32"60 Vitaloni Sabina 21/11/2021 M50 1'13"54 Vitaloni Sabina 09/02/2020 M50
M55 M55 M55
M60 M60 M60
M65 M65 M65
M70 M70 M70
M75 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

DONNE_25_DO = _righe("""
M25 31"38 Lugano Diletta 11/12/2011 M25 1'05"43 Lugano Diletta 04/03/2012 M25 2'22"79 Lugano Diletta 15/02/2009
M30 31"38 Lugano Diletta 21/02/2015 M30 1'06"41 Lugano Diletta 22/02/2015 M30 2'24"23 Lugano Diletta 08/03/2015
M35 32"85 Lugano Diletta 16/02/2020 M35 1'12"62 Capuzzi Valentina 22/02/2015 M35 2'35"89 Capuzzi Valentina 14/12/2014
M40 35"81 Tava Francesca 19/02/2017 M40 1'18"44 Tava Francesca 03/12/2017 M40 2'45"92 Lugano Valentina 12/02/2022
M45 36"75 Tava Francesca 22/01/2023 M45 1'17"66 Tava Francesca 20/02/2022 M45 2'45"11 Tava Francesca 04/02/2022
M50 38"40 Tava Francesca 08/02/2025 M50 1'21"84 Tava Francesca 30/03/2025 M50 3'08"44 Dematti Delia 16/02/2020
M55 55"49 Rolando Ida 15/12/2013 M55 1'30"94 Ferrari Stefania 19/12/2021 M55 3'12"22 Ferrari Stefania 20/02/2022
M60 51"67 Valloni Susanna 11/02/2018 M60 2'11"92 Bettello Licia 22/12/2019 M60
M65 49"97 Valloni Susanna 15/02/2020 M65 2'25"46 Alice Irene 11/02/2007 M65
M70 1'05"89 Alice Irene 23/12/2007 M70 M70
M75 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

DONNE_25_RA = _righe("""
M25 35"10 Frattini Francesca 22/02/2015 M25 1'22"30 Baretella Gloria 15/02/2020 M25 2'56"27 Pastore Francesca 15/04/2012
M30 36"42 Colorio Barbara 11/02/2006 M30 1'21"29 Colorio Barbara 03/12/2005 M30 2'57"00 Colorio Barbara 12/02/2006
M35 39"55 Galliano Barbara 22/02/2015 M35 1'25"34 Pastore Francesca 02/12/2018 M35 3'21"30 Lugano Valentina 24/02/2019
M40 35"60 Vitaloni Sabina 11/02/2018 M40 1'16"66 Vitaloni Sabina 10/03/2013 M40 2'48"85 Vitaloni Sabina 29/04/2012
M45 35"06 Vitaloni Sabina 03/04/2016 M45 1'16"52 Vitaloni Sabina 08/03/2015 M45 2'49"91 Vitaloni Sabina 11/02/2018
M50 35"65 Vitaloni Sabina 07/12/2024 M50 1'18"90 Vitaloni Sabina 08/12/2024 M50 2'54"17 Vitaloni Sabina 10/03/2024
M55 35"83 Vitaloni Sabina 15/02/2025 M55 1'18"66 Vitaloni Sabina 15/02/2025 M55 2'55"77 Vitaloni Sabina 12/01/2025
M60 M60 2'13"30 Bettello Licia 22/12/2019 M60 4'32"27 Bettello Licia 15/02/2020
M65 1'03"46 Bettello Licia 20/02/2022 M65 2'10"68 Bettello Licia 27/02/2021 M65
M70 1'22"25 Alice Irene 12/12/2010 M70 M70
M75 1'21"25 Bois Gabriella 16/02/2020 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

DONNE_25_MX = _righe("""
M25 1'08"56 Lugano Diletta 05/03/2009 M25 2'27"67 Frattini Francesca 21/04/2013 M25 5'15"76 Lugano Diletta 19/04/2009
M30 1'10"87 Lugano Diletta 15/11/2015 M30 2'30"94 Colorio Barbara 26/03/2006 M30 5'33"30 Colorio Barbara 04/02/2006
M35 1'13"71 Lugano Diletta 28/10/2019 M35 2'45"22 Pastore Francesca 10/02/2018 M35 5'51"79 Lugano Valentina 24/02/2019
M40 1'10"67 Vitaloni Sabina 15/04/2013 M40 2'35"19 Vitaloni Sabina 20/02/2011 M40 5'53"40 Lugano Valentina 23/02/2020
M45 1'10"07 Vitaloni Sabina 06/01/2016 M45 2'32"96 Vitaloni Sabina 16/03/2016 M45
M50 1'12"55 Vitaloni Sabina 15/02/2020 M50 3'30"97 Cerchi Claudia 18/02/2024 M50 6'19"70 Tava Francesca 13/04/2025
M55 1'13"73 Vitaloni Sabina 06/04/2025 M55 M55
M60 1'45"89 Valloni Susanna 11/02/2018 M60 M60
M65 2'28"80 Alice Irene 29/04/2007 M65 M65
M70 M70 M70
M75 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

DONNE_50_SL = _righe("""
M25 28"50 Lugano Diletta Mondiali 2012 M25 1'01"69 Anfossi Giulia Mondiali 2012 M25 2'20"27 Lugano Diletta 04/05/2013 M25 5'04"18 Pastore Francesca Italiani 2011 M25 10'19"48 Scaramel Cristiana 13/03/2004 M25 20'45"30 Scaramel Cristiana 07/07/2005
M30 27"87 Dematti Delia Italiani 2003 M30 1'02"95 Dematti Delia 31/05/2003 M30 2'21"68 Colorio Barbara 14/05/2006 M30 4'54"03 Colombo Silvia 10/08/2006 M30 10'06"29 Lugano Valentina Europei 2013 M30 20'03"39 Lugano Valentina 01/02/2014
M35 27"56 Dematti Delia 23/11/2003 M35 1'04"33 Michelon Jessica Italiani 2024 M35 2'21"93 Dematti Delia 28/06/2007 M35 5'02"13 Lugano Valentina Italiani 2019 M35 10'24"61 Lugano Valentina Italiani 2019 M35 20'03"43 Lugano Valentina 08/04/2018
M40 29"54 Vitaloni Sabina 24/05/2014 M40 1'06"63 Lugano Valentina 18/06/2021 M40 2'22"74 Lugano Valentina Italiani 2022 M40 4'59"45 Lugano Valentina Italiani 2023 M40 10'17"11 Lugano Valentina Mondiali 2024 M40 19'41"64 Lugano Valentina 08/06/2024
M45 28"98 Vitaloni Sabina Italiani 2017 M45 1'05"21 Vitaloni Sabina 08/04/2018 M45 2'25"57 Lugano Valentina Italiani 2025 M45 5'02"70 Lugano Valentina Italiani 2025 M45 10'20"42 Lugano Valentina Italiani 2025 M45 19'44"36 Lugano Valentina 07/06/2025
M50 30"44 Vitaloni Sabina 21/05/2022 M50 1'17"60 Bertoni Marina 04/05/2025 M50 2'34"15 Tava Francesca Italiani 2025 M50 5'28"55 Tava Francesca 04/05/2025 M50 11'25"53 Tava Francesca Italiani 2025 M50 25'47"08 Cerchi Claudia 18/05/2025
M55 30"53 Vitaloni Sabina 08/06/2025 M55 1'25"34 Rolando Ida Mondiali 2012 M55 3'07"88 Rolando Ida 29/05/2012 M55 6'39"15 Rolando Ida Mondiali 2012 M55 13'27"13 Ferrari Stefania Italiani 2022 M55 27'03"35 Rolando Ida 01/02/2014
M60 52"89 Villano Gloria 22/05/2011 M60 1'28"86 Rolando Ida 30/04/2016 M60 3'11"07 Rolando Ida 30/04/2016 M60 6'48"39 Rolando Ida 14/05/2016 M60 M60
M65 43"64 Rolando Ida 06/06/2021 M65 1'33"26 Rolando Ida 26/06/2021 M65 4'11"56 Alice Irene 27/05/2007 M65 7'06"07 Rolando Ida 06/06/2021 M65 15'01"66 Rolando Ida 26/06/2021 M65
M70 1'00"72 Alice Irene 17/05/2010 M70 M70 4'18"14 Alice Irene 26/06/2008 M70 8'56"34 Alice Irene 25/06/2008 M70 M70
M75 1'08"05 Bois Gabriella 06/06/2021 M75 M75 M75 10'30"71 Bois Gabriella 06/06/2021 M75 M75
M80 M80 M80 M80 M80 M80
M85 M85 M85 M85 M85 M85
M90 M90 M90 M90 M90 M90
""")

DONNE_50_DF = _righe("""
M25 29"67 Anfossi Giulia Mondiali 2012 M25 1'06"14 Anfossi Giulia Mondiali 2012 M25
M30 29"80 Lugano Diletta 31/05/2015 M30 1'10"49 Colombo Silvia 01/07/2006 M30 2'36"93 Colombo Silvia 10/08/2006
M35 30"75 Dematti Delia 05/03/2005 M35 M35
M40 31"84 Vitaloni Sabina 13/05/2017 M40 M40
M45 31"97 Vitaloni Sabina 26/05/2018 M45 1'12"52 Vitaloni Sabina 06/05/2018 M45
M50 41"52 Cerchi Claudia 04/05/2025 M50 1'39"04 Cerchi Claudia 02/06/2025 M50
M55 M55 M55
M60 M60 M60
M65 M65 M65
M70 M70 M70
M75 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

DONNE_50_DO = _righe("""
M25 31"99 Lugano Diletta Europei 2013 M25 1'07"19 Lugano Diletta Italiani 2009 M25 2'26"55 Lugano Diletta Italiani 2009
M30 31"83 Lugano Diletta Italiani 2015 M30 1'07"66 Lugano Diletta Italiani 2015 M30 2'27"57 Lugano Diletta Italiani 2015
M35 33"92 Lugano Diletta Italiani 2019 M35 1'12"59 Lugano Diletta Italiani 2019 M35 2'40"62 Capuzzi Valentina Italiani 2015
M40 36"57 Tava Francesca Italiani 2017 M40 1'20"60 Tava Francesca Italiani 2017 M40 2'55"41 Tava Francesca Italiani 2017
M45 37"67 Coppero Simona 09/04/2017 M45 1'20"55 Tava Francesca Italiani 2022 M45 2'51"81 Tava Francesca Italiani 2022
M50 38"82 Tava Francesca Italiani 2025 M50 M50 2'57"23 Tava Francesca Italiani 2025
M55 42"61 Ferrari Stefania Italiani 2023 M55 1'34"03 Ferrari Stefania 06/06/2021 M55 3'14"65 Ferrari Stefania Italiani 2022
M60 51"35 Valloni Susanna 02/06/2018 M60 M60
M65 M65 2'14"27 Bettello Licia 06/06/2021 M65
M70 1'08"23 Alice Irene 28/06/2008 M70 M70
M75 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

DONNE_50_RA = _righe("""
M25 36"49 Frattini Francesca Italiani 2015 M25 1'27"79 Moroni Sara Mondiali 2012 M25 2'57"67 Pastore Francesca Italiani 2011
M30 36"34 Colorio Barbara 10/08/2006 M30 1'20"16 Colorio Barbara 10/08/2006 M30 2'53"70 Colorio Barbara 10/08/2006
M35 50"36 Como Daria 30/04/2016 M35 1'30"58 Pastore Francesca 06/05/2018 M35 3'40"87 Valenza Sonia 08/05/2022
M40 35"12 Vitaloni Sabina 01/05/2012 M40 1'18"52 Vitaloni Sabina Mondiali 2012 M40 2'54"44 Vitaloni Sabina Italiani 2011
M45 34"91 Vitaloni Sabina Italiani 2016 M45 1'18"25 Vitaloni Sabina Mondiali 2017 M45 2'54"07 Vitaloni Sabina Italiani 2015
M50 36"20 Vitaloni Sabina Mondiali 2024 M50 1'19"85 Vitaloni Sabina Italiani 2024 M50 2'58"85 Vitaloni Sabina Italiani 2024
M55 36"08 Vitaloni Sabina 04/05/2025 M55 1'20"82 Vitaloni Sabina Italiani 2025 M55 2'58"53 Vitaloni Sabina Italiani 2025
M60 M60 M60
M65 M65 2'14"68 Bettello Licia 06/06/2021 M65
M70 1'23"36 Alice Irene 17/05/2010 M70 M70
M75 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

DONNE_50_MX = _righe("""
M25 M25 2'31"56 Lugano Diletta Italiani 2009 M25 5'41"71 Lugano Diletta Mondiali 2010
M30 M30 2'35"06 Colorio Barbara 10/08/2006 M30 5'44"40 Colorio Barbara 06/05/2006
M35 M35 3'12"29 Valenza Sonia 05/06/2022 M35
M40 M40 2'37"97 Vitaloni Sabina Europei 2013 M40
M45 M45 2'37"66 Vitaloni Sabina Europei 2016 M45
M50 M50 3'07"57 Tava Francesca 08/06/2025 M50
M55 M55 M55
M60 M60 M60
M65 M65 M65
M70 M70 M70
M75 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

UOMINI_25_SL = _righe("""
M25 24"51 Maranzana Nicolò 19/02/2017 M25 53"74 Foglio Alessandro 15/04/2021 M25 1'55"55 Foglio Alessandro 03/04/2016 M25 4'06"98 Foglio Alessandro 16/12/2012 M25 8'48"5 Foglio Alessandro 10/03/2013 M25 16'43"46 Affricano Fabio 14/02/2004
M30 23"85 Galvagno Michele 03/04/2011 M30 53"59 Galvagno Michele 27/02/2011 M30 1'59"39 Galvagno Michele 05/12/2010 M30 4'14"40 Affricano Fabio 27/10/2007 M30 8'34"69 Affricano Fabio 28/11/2004 M30 16'31"60 Affricano Fabio 02/06/2007
M35 24"05 Galvagno Michele 21/04/2013 M35 54"24 Galvagno Michele 21/04/2013 M35 2'03"33 Galvagno Michele 30/11/2014 M35 4'20"69 Foglio Alessandro 19/02/2022 M35 9'10"50 Ferrari Andrea 19/02/2022 M35 18'02"42 Ferrari Andrea 12/02/2022
M40 24"68 Galvagno Michele 18/03/2018 M40 55"68 Galvagno Michele 18/03/2018 M40 2'07"70 Assandri Emiliano 08/03/2015 M40 4'31"33 Assandri Emiliano 23/02/2014 M40 9'29"90 Assandri Emiliano 23/03/2014 M40 18'43"58 Gerbi Paolo 29/04/2007
M45 25"98 Mariani Riccardo 25/03/2018 M45 57"85 Gerbi Paolo 26/01/2008 M45 2'06"49 Gerbi Paolo 26/01/2008 M45 4'33"47 Gerbi Paolo 29/03/2008 M45 9'33"23 Gerbi Paolo 09/02/2008 M45 18'32"44 Gerbi Paolo 14/02/2009
M50 27"13 Pellegrini Michele 06/02/2025 M50 58"43 Pellegrini Michele 19/02/2024 M50 2'09"46 Scaramel Giannantonio 18/01/2004 M50 4'37"74 Scaramel Giannantonio 27/03/2004 M50 9'39"10 Scaramel Giannantonio 26/11/2005 M50 18'44"60 Scaramel Giannantonio 12/02/2006
M55 27"20 Vigneri Luca 10/03/2024 M55 1'02"48 Scaramel Giannantonio 29/11/2009 M55 2'10"92 Vigneri Luca 07/04/2024 M55 4'38"79 Scaramel Giannantonio 15/02/2009 M55 9'37"40 Scaramel Giannantonio 15/02/2009 M55 18'36"16 Scaramel Giannantonio 01/03/2009
M60 30"95 Scaramel Giannantonio 29/04/2012 M60 1'06"60 Scaramel Giannantonio 15/01/2012 M60 2'22"19 Scaramel Giannantonio 03/11/2013 M60 4'55"73 Scaramel Giannantonio 26/02/2012 M60 10'10"20 Scaramel Giannantonio 12/02/2012 M60 19'47"20 Scaramel Giannantonio 04/03/2012
M65 31"94 Scaramel Giannantonio 22/01/2017 M65 1'09"22 Scaramel Giannantonio 02/04/2017 M65 2'29"72 Scaramel Giannantonio 10/11/2019 M65 5'03"91 Scaramel Giannantonio 23/02/2020 M65 10'39"99 Scaramel Giannantonio 17/02/2019 M65 20'14"49 Scaramel Giannantonio 16/02/2020
M70 34"02 Scaramel Giannantonio 13/02/2022 M70 1'16"16 Scaramel Giannantonio 20/11/2022 M70 2'34"59 Scaramel Giannantonio 22/01/2023 M70 5'18"12 Scaramel Giannantonio 13/02/2022 M70 11'00"05 Scaramel Giannantonio 11/02/2023 M70 20'45"67 Scaramel Giannantonio 20/02/2022
M75 M75 M75 M75 M75 M75
M80 M80 2'01"12 Rissone Elios 21/01/2018 M80 M80 9'10"58 Rissone Elios 12/11/2017 M80 18'48"91 Rissone Elios 11/02/2018 M80
M85 M85 M85 M85 M85 M85
M90 M90 M90 M90 M90 M90
""")

UOMINI_25_DF = _righe("""
M25 26"27 Dal Bo Luca 28/04/2024 M25 58"89 Foglio Alessandro 13/12/2015 M25 2'09"55 Foglio Alessandro 21/02/2016
M30 26"80 Galvagno Michele 01/03/2009 M30 59"80 Foglio Alessandro 18/03/2018 M30 2'13"00 Foglio Alessandro 19/02/2017
M35 26"94 Galvagno Michele 23/03/2014 M35 1'01"44 Galvagno Michele 21/02/2015 M35 2'36"93 Prato Andrea 27/04/2008
M40 27"33 Galvagno Michele 11/02/2018 M40 1'02"08 Kormendi Daniel Marius 10/03/2013 M40 2'26"72 Uncescu Cristinel 08/12/2006
M45 29"16 Kormendi Daniel Marius 21/01/2018 M45 1'04"74 Kormendi Daniel Marius 02/12/2018 M45 2'29"12 Gerbi Paolo 27/04/2008
M50 30"64 Prato Andrea 22/12/2024 M50 1'09"59 Gerbi Paolo 01/12/2013 M50 2'42"41 Scaramel Giannantonio 07/11/2004
M55 32"07 Aglieta Cesare 21/01/2018 M55 1'13"37 Scaramel Giannantonio 13/12/2009 M55 2'48"46 Scaramel Giannantonio 05/12/2010
M60 34"79 Scaramel Giannantonio 08/01/2012 M60 1'16"83 Scaramel Giannantonio 04/03/2012 M60 2'45"70 Scaramel Giannantonio 12/02/2012
M65 37"09 Scaramel Giannantonio 15/01/2017 M65 1'20"30 Scaramel Giannantonio 31/03/2019 M65 2'53"14 Scaramel Giannantonio 23/04/2017
M70 38"56 Scaramel Giannantonio 10/04/2022 M70 M70 3'02"45 Scaramel Giannantonio 27/03/2022
M75 M75 M75
M80 M80 3'43"70 Rissone Elios 18/03/2018 M80
M85 M85 M85
M90 M90 M90
""")

UOMINI_25_DO = _righe("""
M25 29"64 Foglio Alessandro 22/02/2015 M25 1'01"00 Foglio Alessandro 17/04/2016 M25 2'10"26 Affricano Fabio 07/02/2004
M30 29"33 Foglio Alessandro 19/02/2017 M30 1'02"03 Foglio Alessandro 18/03/2018 M30 2'09"82 Affricano Fabio 12/03/2005
M35 29"52 Assandri Emiliano 14/02/2010 M35 1'02"32 Assandri Emiliano 08/12/2009 M35 2'15"54 Assandri Emiliano 13/12/2009
M40 29"72 Assandri Emiliano 13/04/2014 M40 1'02"92 Assandri Emiliano 19/04/2015 M40 2'18"97 Assandri Emiliano 21/02/2016
M45 31"12 Assandri Emiliano 11/02/2018 M45 1'06"32 Assandri Emiliano 18/03/2018 M45 2'25"22 Affricano Fabio 27/02/2021
M50 34"43 Prato Andrea 08/03/2025 M50 1'16"40 Scaramel Giannantonio 28/11/2004 M50 2'39"39 Bonadei Giuliano 28/04/2013
M55 33"49 Aglieta Cesare 11/02/2018 M55 1'07"06 Vigneri Luca 07/04/2024 M55 2'24"00 Vigneri Luca 10/03/2024
M60 38"13 Scaramel Giannantonio 26/01/2013 M60 1'22"24 Scaramel Giannantonio 21/04/2013 M60 2'45"79 Scaramel Giannantonio 16/12/2012
M65 38"43 Scaramel Giannantonio 19/03/2017 M65 1'22"26 Scaramel Giannantonio 02/04/2017 M65 2'51"73 Scaramel Giannantonio 23/04/2017
M70 42"46 Scaramel Giannantonio 18/02/2023 M70 1'28"93 Scaramel Giannantonio 05/03/2023 M70 3'07"69 Scaramel Giannantonio 04/12/2022
M75 M75 M75
M80 1'01"20 Rissone Elios 11/02/2018 M80 M80 4'53"74 Rissone Elios 11/02/2018
M85 M85 M85
M90 M90 M90
""")

UOMINI_25_RA = _righe("""
M25 30"44 Menato Alessandro 20/02/2022 M25 1'07"83 Scaramel Luca 25/04/2004 M25 2'31"69 Scaramel Luca 07/02/2004
M30 30"10 Battiston Simone 18/12/2005 M30 1'05"01 Battiston Simone 12/03/2006 M30 2'22"56 Battiston Simone 18/12/2005
M35 30"52 Gallazzi Emiliano 15/04/2012 M35 1'07"35 Battiston Simone 20/02/2011 M35 2'21"36 Battiston Simone 13/12/2009
M40 31"42 Kormendi Daniel Marius 15/04/2013 M40 1'09"26 Coscia Christian 03/12/2017 M40 2'38"68 Coscia Christian 23/02/2020
M45 32"10 Coscia Christian 12/12/2021 M45 1'09"90 Coscia Christian 19/12/2021 M45 2'39"40 Coscia Christian 19/02/2022
M50 35"40 Prato Andrea 04/12/2022 M50 1'18"20 Scaramel Giannantonio 12/02/2006 M50 2'48"64 Scaramel Giannantonio 14/11/2004
M55 36"34 Scaramel Giannantonio 26/11/2006 M55 1'16"10 Scaramel Giannantonio 04/01/2009 M55 2'45"28 Scaramel Giannantonio 14/12/2008
M60 37"87 Scaramel Giannantonio 29/01/2012 M60 1'19"40 Scaramel Giannantonio 29/04/2012 M60 2'54"52 Scaramel Giannantonio 11/12/2011
M65 39"80 Scaramel Giannantonio 19/01/2020 M65 1'24"96 Scaramel Giannantonio 01/05/2017 M65 3'04"05 Scaramel Giannantonio 19/03/2017
M70 42"12 Scaramel Giannantonio 09/01/2022 M70 M70 3'10"62 Scaramel Giannantonio 10/04/2022
M75 M75 M75
M80 1'08"86 Rissone Elios 07/01/2018 M80 2'32"93 Rissone Elios 19/11/2017 M80
M85 M85 M85
M90 M90 M90
""")

UOMINI_25_MX = _righe("""
M25 1'00"45 Dal Bo Luca 28/04/2024 M25 2'13"91 Foglio Alessandro 25/11/2012 M25 4'43"18 Foglio Alessandro 27/02/2016
M30 1'00"60 Battiston Simone 23/04/2006 M30 2'13"03 Battiston Simone 12/11/2005 M30 4'46"12 Affricano Fabio 18/12/2005
M35 1'00"46 Battiston Simone 08/12/2009 M35 2'15"94 Battiston Simone 31/01/2010 M35 5'17"33 Prato Andrea 09/12/2007
M40 1'04"88 Kormendi Daniel Marius 02/12/2012 M40 2'27"64 Coscia Christian 28/02/2016 M40 5'15"13 Gerbi Paolo 15/04/2007
M45 1'06"58 Coscia Christian 11/02/2023 M45 2'27"73 Gerbi Paolo 24/02/2008 M45 5'18"89 Gerbi Paolo 01/12/2007
M50 1'09"60 Prato Andrea 04/12/2022 M50 2'33"44 Gerbi Paolo 03/11/2013 M50 5'29"70 Scaramel Giannantonio 16/04/2005
M55 1'13"42 Scaramel Giannantonio 11/03/2007 M55 2'33"94 Scaramel Giannantonio 28/01/2007 M55 5'37"69 Scaramel Giannantonio 15/04/2007
M60 1'15"90 Scaramel Giannantonio 02/12/2012 M60 2'37"83 Scaramel Giannantonio 26/02/2012 M60 5'40"49 Scaramel Giannantonio 08/01/2012
M65 1'18"64 Scaramel Giannantonio 25/03/2017 M65 2'46"55 Scaramel Giannantonio 17/03/2019 M65 5'59"95 Scaramel Giannantonio 07/01/2018
M70 1'28"82 Scaramel Giannantonio 11/02/2023 M70 3'07"09 Scaramel Giannantonio 16/04/2023 M70 6'08"39 Scaramel Giannantonio 09/01/2022
M75 M75 M75
M80 2'26"87 Rissone Elios 03/12/2017 M80 5'15"19 Rissone Elios 18/03/2018 M80 11'49"40 Rissone Elios 07/01/2018
M85 M85 M85
M90 M90 M90
""")

UOMINI_50_SL = _righe("""
M25 25"21 Maranzana Nicolò Italiani 2017 M25 56"01 Foglio Alessandro 01/06/2014 M25 1'59"89 Foglio Alessandro Mondiali 2012 M25 4'14"62 Foglio Alessandro Mondiali 2012 M25 8'54"24 Affricano Fabio 13/03/2004 M25 18'06"00 Ferrari Andrea 23/10/2016
M30 24"53 Galvagno Michele Italiani 2011 M30 54"32 Galvagno Michele Italiani 2011 M30 2'02"82 Galvagno Michele Italiani 2010 M30 4'19"41 Affricano Fabio europei 2005 M30 8'50"33 Affricano Fabio europei 2005 M30 17'08"40 Affricano Fabio 04/02/2006
M35 24"61 Galvagno Michele Italiani 2014 M35 55"01 Galvagno Michele Europei 2013 M35 2'09"65 Galvagno Michele 16/02/2014 M35 5'11"25 Mogni Riccardo 04/03/2006 M35 10'13"15 Prato Andrea 23/06/2008 M35 20'51"52 Mogni Riccardo 04/06/2006
M40 25"17 Galvagno Michele italiani 2018 M40 56"18 Galvagno Michele italiani 2018 M40 2'08"88 Gerbi Paolo 29/06/2007 M40 4'37"93 Gerbi Paolo 26/06/2007 M40 9'46"90 Gerbi Paolo 13/05/2007 M40 19'06"00 Assandri Emiliano 30/04/2016
M45 27"01 Kormendi Daniel Marius 19/05/2018 M45 1'02"61 Gerbi Paolo 13/05/2012 M45 2'10"29 Gerbi Paolo 26/06/2008 M45 4'42"42 Gerbi Paolo 25/06/2008 M45 9'51"16 Gerbi Paolo 01/06/2008 M45 24'16"26 Leggio Sergio 01/02/2014
M50 29"49 Scaramel Giannantonio 31/05/2003 M50 59"99 Pellegrini Michele Italiani 2003 M50 2'11"90 Pellegrini Michele 02/06/2023 M50 4'42"75 Scaramel Giannantonio 29/06/2004 M50 9'45"51 Scaramel Giannantonio mondiali 2004 M50 19'02"00 Scaramel Giannantonio 28/05/2005
M55 29"11 Aglieta Cesare italiani 2018 M55 1'09"13 Aglieta Cesare 06/05/2018 M55 2'17"31 Scaramel Giannantonio europei 2009 M55 4'47"00 Scaramel Giannantonio europei 2009 M55 9'55"59 Scaramel Giannantonio europei 2009 M55 19'12"00 Scaramel Giannantonio 01/11/2009
M60 43"95 Curone Giovanni 01/06/2008 M60 1'36"89 Curone Giovanni 01/06/2008 M60 2'23"50 Scaramel Giannantonio Italiani 2012 M60 5'02"24 Scaramel Giannantonio Europei 2013 M60 10'25"21 Scaramel Giannantonio Mondiali 2012 M60 20'16"00 Scaramel Giannantonio 04/05/2013
M65 44"88 Curone Giovanni 28/05/2012 M65 1'12"49 Scaramel Giannantonio 22/04/2018 M65 2'32"01 Scaramel Giannantonio 07/04/2019 M65 5'17"91 Scaramel Giannantonio Italiani 2018 M65 10'58"03 Scaramel Giannantonio Italiani 2019 M65
M70 M70 M70 2'36"24 Scaramel Giannantonio Italiani 2022 M70 5'28"17 Scaramel Giannantonio Italiani 2022 M70 11'11"57 Scaramel Giannantonio Italiani 2022 M70 21'30"18 Scaramel Giannantonio 11/06/2022
M75 M75 M75 M75 M75 M75
M80 M80 2'03"14 Rissone Elios italiani 2018 M80 4'34"84 Rissone Elios 02/06/2018 M80 M80 M80 38'27"03 Rissone Elios 08/04/2018
M85 M85 M85 M85 M85 M85
M90 M90 M90 M90 M90 M90
""")

UOMINI_50_DF = _righe("""
M25 27"76 Chiapperini Domenico 01/07/2006 M25 1'00"72 Foglio Alessandro 12/05/2013 M25 2'15"29 Foglio Alessandro Europei 2016
M30 26"27 Galvagno Michele 15/05/2011 M30 1'01"49 Ciccone Alessandro 02/06/2023 M30 2'19"62 Ciccone Alessandro 20/05/2023
M35 26"45 Galvagno Michele Italiani 2013 M35 1'02"22 Kormendi Daniel Marius Mondiali 2012 M35
M40 27"19 Galvagno Michele 02/06/2018 M40 1'08"36 Gerbi Paolo 04/03/2007 M40 2'33"71 Uncescu Cristinel 24/06/2008
M45 29"60 Kormendi Daniel Marius 19/05/2018 M45 1'11"51 Ferrarotti Danilo 08/05/2022 M45
M50 31"18 Prato Andrea Italiani 2025 M50 1'17"49 Gerbi Paolo 31/05/2015 M50 3'19"05 Saracino Vincenzo Italiani 2011
M55 33"34 Aglieta Cesare 08/04/2018 M55 M55 3'01"44 Scaramel Giannantonio 29/06/2007
M60 M60 1'43"53 Ponteprino Mauro 28/05/2022 M60 2'52"29 Scaramel Giannantonio Italiani 2012
M65 M65 1'23"10 Scaramel Giannantonio 09/04/2017 M65 3'08"14 Scaramel Giannantonio Italiani 2017
M70 39"86 Scaramel Giannantonio 20/05/2023 M70 M70 3'28"27 Scaramel Giannantonio 20/05/2023
M75 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

UOMINI_50_DO = _righe("""
M25 30"13 Foglio Alessandro Mondiali 2012 M25 1'04"54 Foglio Alessandro Italiani 2015 M25 2'14"33 Affricano Fabio 06/03/2004
M30 31"96 Balladore Marco Italiani 2023 M30 1'05"50 Affricano Fabio 29/05/2005 M30 2'16"61 Affricano Fabio 05/03/2005
M35 30"39 Assandri Emiliano Italiani 2011 M35 1'05"34 Assandri Emiliano Italiani 2011 M35 2'23"90 Assandri Emiliano Mondiali 2012
M40 30"94 Assandri Emiliano Italiani 2014 M40 1'05"77 Assandri Emiliano Italiani 2015 M40 2'25"04 Assandri Emiliano Italiani 2015
M45 35"27 Guagnini Stefano 28/05/2012 M45 1'14"07 Guagnini Stefano Italiani 2011 M45 2'40"06 Guagnini Stefano Mondiali 2012
M50 35"67 Guagnini Stefano Italiani 2016 M50 1'16"27 Prato Andrea Italiani 2025 M50 2'40"58 Bonadei Giuliano Italiani 2013
M55 34"72 Aglieta Cesare Italiani 2019 M55 1'17"56 Aglieta Cesare Italiani 2018 M55 3'05"96 Aglieta Cesare 26/05/2018
M60 39"95 Scaramel Giannantonio 28/05/2012 M60 1'23"27 Scaramel Giannantonio 13/05/2012 M60
M65 40"43 Scaramel Giannantonio 06/05/2018 M65 1'28"03 Scaramel Giannantonio 08/04/2018 M65
M70 M70 1'37"60 Scaramel Giannantonio 08/05/2022 M70 3'12"71 Scaramel Giannantonio 28/05/2022
M75 M75 M75
M80 M80 2'20"04 Rissone Elios Italiani 2018 M80
M85 M85 M85
M90 M90 M90
""")

UOMINI_50_RA = _righe("""
M25 32"43 Coscia Christian italiani 2002 M25 1'12"75 Coscia Christian mondiali 2004 M25 2'36"89 Scaramel Luca mondiali 2004
M30 30"64 Battiston Simone 14/05/2006 M30 1'07"58 Battiston Simone 28/05/2006 M30 2'27"07 Battiston Simone 04/03/2006
M35 30"94 Gallazzi Emiliano Mondiali 2012 M35 1'08"16 Battiston Simone 20/05/2012 M35 2'27"59 Battiston Simone Italiani 2010
M40 32"12 Coscia Christian Europei 2016 M40 1'11"38 Coscia Christian Italiani 2016 M40 2'50"39 Coscia Christian 26/05/2018
M45 32"70 Coscia Christian Italiani 2022 M45 1'12"98 Coscia Christian Italiani 2022 M45 3'17"04 Poggi Enrico 06/05/2018
M50 41"71 Saracino Vincenzo Mondiali 2012 M50 1'34"56 Saracino Vincenzo Italiani 2011 M50 3'29"21 Saracino Vincenzo Italiani 2010
M55 36"40 Scaramel Giannantonio 17/05/2009 M55 1'24"03 Scaramel Giannantonio Italiani 2011 M55 2'57"43 Scaramel Giannantonio europei 2009
M60 45"98 Saracino Vincenzo 26/06/2021 M60 1'25"35 Scaramel Giannantonio Italiani 2012 M60 3'05"59 Scaramel Giannantonio Mondiali 2012
M65 1'04"75 Curone Giovanni 15/05/2011 M65 M65 3'05"73 Scaramel Giannantonio Italiani 2018
M70 M70 1'40"24 Scaramel Giannantonio 28/05/2022 M70
M75 M75 M75
M80 M80 M80
M85 M85 M85
M90 M90 M90
""")

UOMINI_50_MX = _righe("""
M25 M25 2'18"49 Foglio Alessandro 06/03/2016 M25 4'51"68 Foglio Alessandro Mondiali 2012
M30 M30 2'18"70 Battiston Simone 06/05/2006 M30 4'53"44 Affricano Fabio 14/05/2005
M35 M35 2'17"40 Battiston Simone Mondiali 2010 M35 5'01"59 Battiston Simone 06/06/2010
M40 M40 2'32"99 Coscia Christian Europei 2018 M40 5'38"14 Gerbi Paolo 13/05/2007
M45 M45 2'33"99 Coscia Christian Italiani 2022 M45 6'44"62 Miot Federico 17/05/2025
M50 M50 2'37"47 Scaramel Giannantonio Italiani 2009 M50 5'39"16 Gerbi Paolo 16/02/2014
M55 M55 2'41"52 Scaramel Giannantonio Mondiali 2010 M55 5'33"69 Scaramel Giannantonio Italiani 2009
M60 M60 2'52"61 Scaramel Giannantonio 24/05/2014 M60 5'54"00 Scaramel Giannantonio 01/05/2012
M65 M65 2'53"62 Scaramel Giannantonio Italiani 2019 M65 6'12"23 Scaramel Giannantonio 26/03/2017
M70 M70 3'10"90 Scaramel Giannantonio 08/05/2022 M70
M75 M75 M75
M80 M80 5'43"43 Rissone Elios 22/04/2018 M80 13'05"32 Rissone Elios 02/06/2018
M85 M85 M85
M90 M90 M90
""")

DATI = {
    ("F", 25): {"SL": DONNE_25_SL, "DF": DONNE_25_DF, "DO": DONNE_25_DO, "RA": DONNE_25_RA, "MX": DONNE_25_MX},
    ("F", 50): {"SL": DONNE_50_SL, "DF": DONNE_50_DF, "DO": DONNE_50_DO, "RA": DONNE_50_RA, "MX": DONNE_50_MX},
    ("M", 25): {"SL": UOMINI_25_SL, "DF": UOMINI_25_DF, "DO": UOMINI_25_DO, "RA": UOMINI_25_RA, "MX": UOMINI_25_MX},
    ("M", 50): {"SL": UOMINI_50_SL, "DF": UOMINI_50_DF, "DO": UOMINI_50_DO, "RA": UOMINI_50_RA, "MX": UOMINI_50_MX},
}


def importa():
    app = create_app()
    with app.app_context():
        creati, aggiornati, vuoti = 0, 0, 0
        for (sesso, vasca), stili in DATI.items():
            for stile, righe in stili.items():
                distanze = DISTANZE_PER_STILE[stile]
                for categoria, riga in zip(CATEGORIE_RECORD, righe):
                    if not riga.startswith(categoria):
                        raise ValueError(f"riga {riga!r} non inizia con la categoria attesa {categoria}")
                    celle = _dividi_riga(riga, len(distanze))
                    for distanza, cella_testo in zip(distanze, celle):
                        cella = _parsa_cella(cella_testo)
                        record = RecordSocietario.query.filter_by(
                            sesso=sesso, vasca=vasca, stile=stile, distanza=distanza, categoria=categoria
                        ).first()
                        if cella is None:
                            vuoti += 1
                            continue
                        tempo, nome, data, evento = cella
                        if record:
                            record.tempo, record.nome, record.data, record.evento = tempo, nome, data, evento
                            aggiornati += 1
                        else:
                            db.session.add(RecordSocietario(
                                sesso=sesso, vasca=vasca, stile=stile, distanza=distanza, categoria=categoria,
                                tempo=tempo, nome=nome, data=data, evento=evento,
                            ))
                            creati += 1
        db.session.commit()
        print(f"Record importati: {creati} creati, {aggiornati} aggiornati, {vuoti} celle vuote ignorate.")


if __name__ == "__main__":
    importa()
