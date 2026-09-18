# -*- coding: utf-8 -*-
"""Importa una tantum i record societari storici (Record_Societari master01.03.2021.pdf)
nel database. Rilanciabile in sicurezza: aggiorna (upsert) i record gia' presenti invece
di duplicarli, e non tocca eventuali record aggiunti/modificati successivamente a mano
tramite l'interfaccia admin, a meno che coincidano con una cella qui sotto.

Uso: python import_record_societari.py
"""
from datetime import datetime

from app import create_app
from extensions import db
from models import RecordSocietario

VASCA = 25


def _d(data_str):
    return datetime.strptime(data_str, "%d/%m/%Y").date()


def r(tempo, nome, data_str):
    return (tempo, nome, _d(data_str))


E = None  # nessun record per quella cella


# Ogni voce: categoria -> lista di celle (tempo, nome, data) o E (vuota), una per distanza,
# nello stesso ordine delle distanze dichiarate in records.STILI_RECORD per quello stile.

DATI = {
    "M": {
        "SL": [
            ("M25", [r('24"51', "Maranzana Nicolò", "19/02/2017"), r('50"36', "Balladore Marco", "20/11/2016"),
                     r('1\'55"55', "Foglio Alessandro", "03/04/2016"), r('4\'06"98', "Foglio Alessandro", "16/12/2012"),
                     r('8\'48"5', "Foglio Alessandro", "10/03/2013"), r('16\'43"46', "Affricano Fabio", "14/02/2004")]),
            ("M30", [r('23"85', "Galvagno Michele", "03/04/2011"), r('53"59', "Galvagno Michele", "27/02/2011"),
                     r('1\'59"39', "Galvagno Michele", "05/12/2010"), r('4\'14"40', "Affricano Fabio", "27/10/2007"),
                     r('8\'34"69', "Affricano Fabio", "28/11/2004"), r('16\'31"60', "Affricano Fabio", "02/06/2007")]),
            ("M35", [r('24"05', "Galvagno Michele", "21/04/2013"), r('54"24', "Galvagno Michele", "21/04/2013"),
                     r('2\'03"33', "Galvagno Michele", "30/11/2014"), r('4\'28"02', "Galvagno Michele", "26/10/2013"),
                     r('9\'49"64', "Prato Andrea", "24/02/2008"), r('18\'41"10', "Prato Andrea", "03/11/2007")]),
            ("M40", [r('24"68', "Galvagno Michele", "18/03/2018"), r('55"68', "Galvagno Michele", "18/03/2018"),
                     r('2\'07"70', "Assandri Emiliano", "08/03/2015"), r('4\'31"33', "Assandri Emiliano", "23/02/2014"),
                     r('9\'29"90', "Assandri Emiliano", "23/03/2014"), r('18\'43"58', "Gerbi Paolo", "29/04/2007")]),
            ("M45", [r('25"98', "Mariani Riccardo", "25/03/2018"), r('57"85', "Gerbi Paolo", "26/01/2008"),
                     r('2\'06"49', "Gerbi Paolo", "26/01/2008"), r('4\'33"47', "Gerbi Paolo", "29/03/2008"),
                     r('9\'33"23', "Gerbi Paolo", "09/02/2008"), r('18\'32"44', "Gerbi Paolo", "14/02/2009")]),
            ("M50", [r('28"04', "Gerbi Paolo", "26/01/2013"), r('1\'00"89', "Scaramel Giannantonio", "06/01/2003"),
                     r('2\'09"46', "Scaramel Giannantonio", "18/01/2004"), r('4\'37"74', "Scaramel Giannantonio", "27/03/2004"),
                     r('9\'39"10', "Scaramel Giannantonio", "26/11/2005"), r('18\'44"60', "Scaramel Giannantonio", "12/02/2006")]),
            ("M55", [r('28"60', "Aglieta Cesare", "18/02/2018"), r('1\'02"48', "Scaramel Giannantonio", "29/11/2009"),
                     r('2\'13"25', "Scaramel Giannantonio", "29/11/2009"), r('4\'38"79', "Scaramel Giannantonio", "15/02/2009"),
                     r('9\'37"40', "Scaramel Giannantonio", "15/02/2009"), r('18\'36"16', "Scaramel Giannantonio", "01/03/2009")]),
            ("M60", [r('30"95', "Scaramel Giannantonio", "29/04/2012"), r('1\'06"60', "Scaramel Giannantonio", "15/01/2012"),
                     r('2\'22"19', "Scaramel Giannantonio", "03/11/2013"), r('4\'55"73', "Scaramel Giannantonio", "26/02/2012"),
                     r('10\'10"20', "Scaramel Giannantonio", "12/02/2012"), r('19\'47"20', "Scaramel Giannantonio", "04/03/2012")]),
            ("M65", [r('31"94', "Scaramel Giannantonio", "22/01/2017"), r('1\'09"22', "Scaramel Giannantonio", "02/04/2017"),
                     r('2\'29"72', "Scaramel Giannantonio", "10/11/2019"), r('5\'03"91', "Scaramel Giannantonio", "23/02/2020"),
                     r('10\'39"99', "Scaramel Giannantonio", "17/02/2019"), r('20\'14"49', "Scaramel Giannantonio", "16/02/2020")]),
            ("M70", [r('48"24', "Villa Lelio", "09/03/2008"), r('1\'47"49', "Villa Lelio", "27/04/2008"),
                     r('3\'53"20', "Villa Lelio", "27/04/2008"), E, E, E]),
            ("M75", [E, E, E, E, E, E]),
            ("M80", [E, r('2\'01"12', "Rissone Elios", "21/01/2018"), E, E,
                     r('9\'10"58', "Rissone Elios", "12/11/2017"), r('18\'48"91', "Rissone Elios", "11/02/2018")]),
            ("M85", [E, E, E, E, E, E]),
            ("M90", [E, E, E, E, E, E]),
        ],
        "DF": [
            ("M25", [r('26"99', "Maranzana Nicolò", "22/12/2019"), r('58"89', "Foglio Alessandro", "13/12/2015"),
                     r('2\'09"55', "Foglio Alessandro", "21/02/2016")]),
            ("M30", [r('26"80', "Galvagno Michele", "01/03/2009"), r('59"80', "Foglio Alessandro", "18/03/2018"),
                     r('2\'13"00', "Foglio Alessandro", "19/02/2017")]),
            ("M35", [r('26"94', "Galvagno Michele", "23/03/2014"), r('1\'01"44', "Galvagno Michele", "21/02/2015"),
                     r('2\'36"93', "Prato Andrea", "27/04/2008")]),
            ("M40", [r('27"33', "Galvagno Michele", "11/02/2018"), r('1\'02"08', "Kormendi Daniel Marius", "10/03/2013"),
                     r('2\'26"72', "Uncescu Cristinel", "08/12/2006")]),
            ("M45", [r('29"16', "Kormendi Daniel Marius", "21/01/2018"), r('1\'04"74', "Kormendi Daniel Marius", "02/12/2018"),
                     r('2\'29"12', "Gerbi Paolo", "27/04/2008")]),
            ("M50", [r('33"21', "Ponteprino Mauro", "16/12/2012"), r('1\'09"59', "Gerbi Paolo", "01/12/2013"),
                     r('2\'42"41', "Scaramel Giannantonio", "07/11/2004")]),
            ("M55", [r('32"07', "Aglieta Cesare", "21/01/2018"), r('1\'13"37', "Scaramel Giannantonio", "13/12/2009"),
                     r('2\'48"46', "Scaramel Giannantonio", "05/12/2010")]),
            ("M60", [r('34"79', "Scaramel Giannantonio", "08/01/2012"), r('1\'16"83', "Scaramel Giannantonio", "04/03/2012"),
                     r('2\'45"70', "Scaramel Giannantonio", "12/02/2012")]),
            ("M65", [r('37"09', "Scaramel Giannantonio", "15/01/2017"), r('1\'20"30', "Scaramel Giannantonio", "31/03/2019"),
                     r('2\'53"14', "Scaramel Giannantonio", "23/04/2017")]),
            ("M70", [E, E, E]),
            ("M75", [E, E, E]),
            ("M80", [E, r('3\'43"70', "Rissone Elios", "18/03/2018"), E]),
            ("M85", [E, E, E]),
            ("M90", [E, E, E]),
        ],
        "DO": [
            ("M25", [r('29"64', "Foglio Alessandro", "22/02/2015"), r('1\'01"00', "Foglio Alessandro", "17/04/2016"),
                     r('2\'10"26', "Affricano Fabio", "07/02/2004")]),
            ("M30", [r('29"33', "Foglio Alessandro", "19/02/2017"), r('1\'02"03', "Foglio Alessandro", "18/03/2018"),
                     r('2\'09"82', "Affricano Fabio", "12/03/2005")]),
            ("M35", [r('29"52', "Assandri Emiliano", "14/02/2010"), r('1\'02"32', "Assandri Emiliano", "08/12/2009"),
                     r('2\'15"54', "Assandri Emiliano", "13/12/2009")]),
            ("M40", [r('29"72', "Assandri Emiliano", "13/04/2014"), r('1\'02"92', "Assandri Emiliano", "19/04/2015"),
                     r('2\'18"97', "Assandri Emiliano", "21/02/2016")]),
            ("M45", [r('31"12', "Assandri Emiliano", "11/02/2018"), r('1\'06"32', "Assandri Emiliano", "18/03/2018"),
                     r('2\'25"22', "Affricano Fabio", "27/02/2021")]),
            ("M50", [r('34"95', "Guagnini Stefano", "27/02/2016"), r('1\'16"40', "Scaramel Giannantonio", "28/11/2004"),
                     r('2\'39"39', "Bonadei Giuliano", "28/04/2013")]),
            ("M55", [r('33"49', "Aglieta Cesare", "11/02/2018"), r('1\'15"82', "Aglieta Cesare", "17/02/2019"),
                     r('2\'45"31', "Scaramel Giannantonio", "07/02/2010")]),
            ("M60", [r('38"13', "Scaramel Giannantonio", "26/01/2013"), r('1\'22"24', "Scaramel Giannantonio", "21/04/2013"),
                     r('2\'45"79', "Scaramel Giannantonio", "16/12/2012")]),
            ("M65", [r('38"43', "Scaramel Giannantonio", "19/03/2017"), r('1\'22"26', "Scaramel Giannantonio", "02/04/2017"),
                     r('2\'51"73', "Scaramel Giannantonio", "23/04/2017")]),
            ("M70", [E, E, E]),
            ("M75", [E, E, E]),
            ("M80", [r('1\'01"20', "Rissone Elios", "11/02/2018"), E, r('4\'53"74', "Rissone Elios", "11/02/2018")]),
            ("M85", [E, E, E]),
            ("M90", [E, E, E]),
        ],
        "RA": [
            ("M25", [r('31"27', "Coscia Christian", "25/01/2003"), r('1\'07"83', "Scaramel Luca", "25/04/2004"),
                     r('2\'31"69', "Scaramel Luca", "07/02/2004")]),
            ("M30", [r('30"10', "Battiston Simone", "18/12/2005"), r('1\'05"01', "Battiston Simone", "12/03/2006"),
                     r('2\'22"56', "Battiston Simone", "18/12/2005")]),
            ("M35", [r('30"52', "Gallazzi Emiliano", "15/04/2012"), r('1\'07"35', "Battiston Simone", "20/02/2011"),
                     r('2\'21"36', "Battiston Simone", "13/12/2009")]),
            ("M40", [r('31"42', "Kormendi Daniel Marius", "15/04/2013"), r('1\'09"26', "Coscia Christian", "03/12/2017"),
                     r('2\'38"68', "Coscia Christian", "23/02/2020")]),
            ("M45", [r('32"63', "Kormendi Daniel Marius", "17/02/2019"), r('1\'13"79', "Kormendi Daniel", "22/12/2019"),
                     r('2\'49"18', "Gerbi Paolo", "13/04/2008")]),
            ("M50", [r('36"79', "Scaramel Giannantonio", "21/12/2003"), r('1\'18"20', "Scaramel Giannantonio", "12/02/2006"),
                     r('2\'48"64', "Scaramel Giannantonio", "14/11/2004")]),
            ("M55", [r('36"34', "Scaramel Giannantonio", "26/11/2006"), r('1\'16"10', "Scaramel Giannantonio", "04/01/2009"),
                     r('2\'45"28', "Scaramel Giannantonio", "14/12/2008")]),
            ("M60", [r('37"87', "Scaramel Giannantonio", "29/01/2012"), r('1\'19"40', "Scaramel Giannantonio", "29/04/2012"),
                     r('2\'54"52', "Scaramel Giannantonio", "11/12/2011")]),
            ("M65", [r('39"80', "Scaramel Giannantonio", "19/01/2020"), r('1\'24"96', "Scaramel Giannantonio", "01/05/2017"),
                     r('3\'04"05', "Scaramel Giannantonio", "19/03/2017")]),
            ("M70", [E, E, E]),
            ("M75", [E, E, E]),
            ("M80", [r('1\'08"86', "Rissone Elios", "07/01/2018"), r('2\'32"93', "Rissone Elios", "19/11/2017"), E]),
            ("M85", [E, E, E]),
            ("M90", [E, E, E]),
        ],
        "MX": [
            ("M25", [r('1\'01"83', "Foglio Alessandro", "11/12/2011"), r('2\'13"91', "Foglio Alessandro", "25/11/2012"),
                     r('4\'43"18', "Foglio Alessandro", "27/02/2016")]),
            ("M30", [r('1\'00"60', "Battiston Simone", "23/04/2006"), r('2\'13"03', "Battiston Simone", "12/11/2005"),
                     r('4\'46"12', "Affricano Fabio", "18/12/2005")]),
            ("M35", [r('1\'00"46', "Battiston Simone", "08/12/2009"), r('2\'15"94', "Battiston Simone", "31/01/2010"),
                     r('5\'17"33', "Prato Andrea", "09/12/2007")]),
            ("M40", [r('1\'04"88', "Kormendi Daniel Marius", "02/12/2012"), r('2\'27"64', "Coscia Christian", "28/02/2016"),
                     r('5\'15"13', "Gerbi Paolo", "15/04/2007")]),
            ("M45", [r('1\'07"02', "Kormendi Daniel Marius", "15/02/2020"), r('2\'27"73', "Gerbi Paolo", "24/02/2008"),
                     r('5\'18"89', "Gerbi Paolo", "01/12/2007")]),
            ("M50", [r('1\'11"63', "Gerbi Paolo", "02/12/2012"), r('2\'33"44', "Gerbi Paolo", "03/11/2013"),
                     r('5\'29"70', "Scaramel Giannantonio", "16/04/2005")]),
            ("M55", [r('1\'13"42', "Scaramel Giannantonio", "11/03/2007"), r('2\'33"94', "Scaramel Giannantonio", "28/01/2007"),
                     r('5\'37"69', "Scaramel Giannantonio", "15/04/2007")]),
            ("M60", [r('1\'15"90', "Scaramel Giannantonio", "02/12/2012"), r('2\'37"83', "Scaramel Giannantonio", "26/02/2012"),
                     r('5\'40"49', "Scaramel Giannantonio", "08/01/2012")]),
            ("M65", [r('1\'18"64', "Scaramel Giannantonio", "25/03/2017"), r('2\'46"55', "Scaramel Giannantonio", "17/03/2019"),
                     r('5\'59"95', "Scaramel Giannantonio", "07/01/2018")]),
            ("M70", [E, E, E]),
            ("M75", [E, E, E]),
            ("M80", [r('2\'26"87', "Rissone Elios", "03/12/2017"), r('5\'15"19', "Rissone Elios", "18/03/2018"),
                     r('11\'49"40', "Rissone Elios", "07/01/2018")]),
            ("M85", [E, E, E]),
            ("M90", [E, E, E]),
        ],
    },
    "F": {
        "SL": [
            ("M25", [r('28"28', "Frattini Francesca", "26/01/2013"), r('1\'01"28', "Anfossi Giulia", "15/04/2012"),
                     r('2\'13"66', "Lugano Diletta", "03/11/2013"), r('4\'44"10', "Lugano Diletta", "24/03/2012"),
                     r('10\'16"40', "Scaramel Cristiana", "10/01/2004"), r('19\'30"99', "Valdata Carlotta", "11/02/2018")]),
            ("M30", [r('27"68', "Dematti Delia", "27/04/2003"), r('1\'01"83', "Dematti Delia", "06/04/2003"),
                     r('2\'16"04', "Lugano Diletta", "30/03/2014"), r('4\'49"64', "Lugano Valentina", "26/10/2013"),
                     r('9\'58"99', "Lugano Diletta", "15/11/2015"), r('19\'34"10', "Lugano Valentina", "04/03/2012")]),
            ("M35", [r('27"47', "Dematti Delia", "25/10/2003"), r('1\'00"69', "Dematti Delia", "04/04/2004"),
                     r('2\'17"07', "Dematti Delia", "30/04/2006"), r('4\'50"90', "Dematti Delia", "12/02/2006"),
                     r('10\'09"29', "Lugano Valentina", "11/02/2018"), r('19\'35"02', "Lugano Valentina", "22/02/2015")]),
            ("M40", [r('28"56', "Dematti Delia", "13/12/2009"), r('1\'02"85', "Vitaloni Sabina", "10/03/2013"),
                     r('2\'20"80', "Lugano Valentina", "19/01/2020"), r('4\'53"78', "Lugano Valentina", "15/02/2020"),
                     r('10\'08"60', "Lugano Valentina", "15/02/2020"), r('19\'27"60', "Lugano Valentina", "23/02/2020")]),
            ("M45", [r('28"67', "Vitaloni Sabina", "21/02/2015"), r('1\'03"57', "Vitaloni Sabina", "23/04/2017"),
                     r('2\'29"36', "Dematti Delia", "21/01/2018"), r('5\'26"86', "Dematti Delia", "22/12/2018"),
                     r('13\'40"01', "Kostner Anna Maria", "21/02/2015"), E]),
            ("M50", [r('29"60', "Dematti Delia", "20/01/2019"), r('1\'07"63', "Dematti Delia", "22/12/2019"),
                     r('2\'36"25', "Dematti Delia", "20/01/2019"), r('6\'17"37', "Rolando Ida", "13/12/2009"), E, E]),
            ("M55", [r('38"63', "Rolando Ida", "30/01/2011"), r('1\'24"49', "Rolando Ida", "17/04/2011"),
                     r('3\'03"43', "Rolando Ida", "13/03/2011"), r('6\'27"62', "Rolando Ida", "25/10/2014"),
                     r('13\'27"09', "Rolando Ida", "21/02/2015"), E]),
            ("M60", [r('42"53', "Rolando Ida", "20/01/2019"), r('1\'29"83', "Rolando Ida", "02/12/2018"),
                     r('3\'22"93', "Rolando Ida", "20/01/2019"), r('6\'36"36', "Rolando Ida", "11/12/2016"),
                     r('13\'25"11', "Rolando Ida", "19/02/2017"), E]),
            ("M65", [r('45"15', "Valloni Susanna", "27/02/2021"), r('1\'36"90', "Valloni Susanna", "27/02/2021"),
                     r('4\'18"04', "Alice Irene", "03/12/2006"), E, E, E]),
            ("M70", [r('52"87', "Alice Irene", "28/10/2007"), r('2\'01"73', "Alice Irene", "28/10/2007"),
                     r('4\'14"81', "Alice Irene", "17/11/2007"), r('8\'54"09', "Alice Irene", "23/12/2007"), E, E]),
            ("M75", [r('1\'04"03', "Bois Gabriella", "22/12/2019"), E, E, E,
                     r('10\'07"00', "Bois Gabriella", "22/12/2019"), r('20\'06"08', "Bois Gabriella", "15/02/2020")]),
            ("M80", [E, E, E, E, E, E]),
            ("M85", [E, E, E, E, E, E]),
            ("M90", [E, E, E, E, E, E]),
        ],
        "DF": [
            ("M25", [r('29"69', "Anfossi Giulia", "29/01/2012"), r('1\'05"26', "Anfossi Giulia", "26/02/2012"),
                     r('2\'48"42', "Valdata Carlotta", "22/04/2018")]),
            ("M30", [r('31"10', "Lugano Diletta", "29/11/2015"), r('1\'11"30', "Colorio Barbara", "12/03/2006"),
                     r('2\'39"66', "Colombo Silvia", "25/03/2006")]),
            ("M35", [r('30"46', "Dematti Delia", "21/12/2003"), r('1\'21"30', "Lugano Valentina", "08/02/2019"),
                     r('3\'00"84', "Lugano Valentina", "23/12/2018")]),
            ("M40", [r('31"62', "Vitaloni Sabina", "13/01/2013"), r('1\'43"08', "Kostner Anna", "14/12/2009"), E]),
            ("M45", [r('31"53', "Vitaloni Sabina", "10/04/2016"), E, E]),
            ("M50", [E, r('1\'13"54', "Vitaloni Sabina", "09/02/2020"), E]),
            ("M55", [E, E, E]),
            ("M60", [E, E, E]),
            ("M65", [E, E, E]),
            ("M70", [E, E, E]),
            ("M75", [E, E, E]),
            ("M80", [E, E, E]),
            ("M85", [E, E, E]),
            ("M90", [E, E, E]),
        ],
        "DO": [
            ("M25", [r('31"38', "Lugano Diletta", "11/12/2011"), r('1\'05"43', "Lugano Diletta", "04/03/2012"),
                     r('2\'22"79', "Lugano Diletta", "15/02/2009")]),
            ("M30", [r('31"38', "Lugano Diletta", "21/02/2015"), r('1\'06"41', "Lugano Diletta", "22/02/2015"),
                     r('2\'24"23', "Lugano Diletta", "08/03/2015")]),
            ("M35", [r('32"85', "Lugano Diletta", "16/02/2020"), r('1\'12"62', "Capuzzi Valentina", "22/02/2015"),
                     r('2\'35"89', "Capuzzi Valentina", "14/12/2014")]),
            ("M40", [r('35"81', "Tava Francesca", "19/02/2017"), r('1\'18"44', "Tava Francesca", "03/12/2017"),
                     r('2\'47"72', "Tava Francesca", "11/02/2018")]),
            ("M45", [r('36"82', "Tava Francesca", "15/02/2020"), r('1\'17"97', "Tava Francesca", "27/02/2021"),
                     r('2\'47"13', "Tava Francesca", "27/02/2021")]),
            ("M50", [E, E, r('3\'08"44', "Dematti Delia", "16/02/2020")]),
            ("M55", [r('55"49', "Rolando Ida", "15/12/2013"), E, E]),
            ("M60", [r('51"67', "Valloni Susanna", "11/02/2018"), r('2\'11"92', "Bettello Licia", "22/12/2019"), E]),
            ("M65", [r('49"97', "Valloni Susanna", "15/02/2020"), r('2\'25"46', "Alice Irene", "11/02/2007"), E]),
            ("M70", [r('1\'05"89', "Alice Irene", "23/12/2007"), E, E]),
            ("M75", [E, E, E]),
            ("M80", [E, E, E]),
            ("M85", [E, E, E]),
            ("M90", [E, E, E]),
        ],
        "RA": [
            ("M25", [r('35"10', "Frattini Francesca", "22/02/2015"), r('1\'22"30', "Baretella Gloria", "15/02/2020"),
                     r('2\'56"27', "Pastore Francesca", "15/04/2012")]),
            ("M30", [r('36"42', "Colorio Barbara", "11/02/2006"), r('1\'21"29', "Colorio Barbara", "03/12/2005"),
                     r('2\'57"00', "Colorio Barbara", "12/02/2006")]),
            ("M35", [r('39"55', "Galliano Barbara", "22/02/2015"), r('1\'25"34', "Pastore Francesca", "02/12/2018"),
                     r('3\'21"30', "Lugano Valentina", "24/02/2019")]),
            ("M40", [r('35"60', "Vitaloni Sabina", "11/02/2018"), r('1\'16"66', "Vitaloni Sabina", "10/03/2013"),
                     r('2\'48"85', "Vitaloni Sabina", "29/04/2012")]),
            ("M45", [r('35"06', "Vitaloni Sabina", "03/04/2016"), r('1\'16"52', "Vitaloni Sabina", "08/03/2015"),
                     r('2\'49"91', "Vitaloni Sabina", "11/02/2018")]),
            ("M50", [r('35"98', "Vitaloni Sabina", "09/02/2020"), E, E]),
            ("M55", [r('53"86', "Rolando Ida", "29/11/2015"), E, E]),
            ("M60", [E, r('2\'13"30', "Bettello Licia", "22/12/2019"), r('4\'32"27', "Bettello Licia", "15/02/2020")]),
            ("M65", [r('1\'11"49', "Alice Irene", "15/04/2007"), r('2\'10"68', "Bettello Licia", "27/02/2021"), E]),
            ("M70", [r('1\'22"25', "Alice Irene", "12/12/2010"), E, E]),
            ("M75", [r('1\'21"25', "Bois Gabriella", "16/02/2020"), E, E]),
            ("M80", [E, E, E]),
            ("M85", [E, E, E]),
            ("M90", [E, E, E]),
        ],
        "MX": [
            ("M25", [r('1\'08"56', "Lugano Diletta", "05/03/2009"), r('2\'27"67', "Frattini Francesca", "21/04/2013"),
                     r('5\'15"76', "Lugano Diletta", "19/04/2009")]),
            ("M30", [r('1\'10"87', "Lugano Diletta", "15/11/2015"), r('2\'30"94', "Colorio Barbara", "26/03/2006"),
                     r('5\'33"30', "Colorio Barbara", "04/02/2006")]),
            ("M35", [r('1\'13"71', "Lugano Diletta", "28/10/2019"), r('2\'45"22', "Pastore Francesca", "10/02/2018"),
                     r('5\'51"79', "Lugano Valentina", "24/02/2019")]),
            ("M40", [r('1\'10"67', "Vitaloni Sabina", "15/04/2013"), r('2\'35"19', "Vitaloni Sabina", "20/02/2011"),
                     r('5\'53"40', "Lugano Valentina", "23/02/2020")]),
            ("M45", [r('1\'10"07', "Vitaloni Sabina", "06/01/2016"), r('2\'32"96', "Vitaloni Sabina", "16/03/2016"), E]),
            ("M50", [r('1\'12"55', "Vitaloni Sabina", "15/02/2020"), E, E]),
            ("M55", [r('1\'56"81', "Rolando Ida", "31/10/2015"), E, E]),
            ("M60", [r('1\'45"89', "Valloni Susanna", "11/02/2018"), E, E]),
            ("M65", [r('2\'28"80', "Alice Irene", "29/04/2007"), E, E]),
            ("M70", [E, E, E]),
            ("M75", [E, E, E]),
            ("M80", [E, E, E]),
            ("M85", [E, E, E]),
            ("M90", [E, E, E]),
        ],
    },
}


def importa():
    app = create_app()
    with app.app_context():
        creati, aggiornati = 0, 0
        for sesso, stili in DATI.items():
            for stile, righe in stili.items():
                for categoria, celle in righe:
                    distanze = {"SL": [50, 100, 200, 400, 800, 1500], "DF": [50, 100, 200],
                                "DO": [50, 100, 200], "RA": [50, 100, 200], "MX": [100, 200, 400]}[stile]
                    for distanza, cella in zip(distanze, celle):
                        if cella is None:
                            continue
                        tempo, nome, data = cella
                        record = RecordSocietario.query.filter_by(
                            sesso=sesso, vasca=VASCA, stile=stile, distanza=distanza, categoria=categoria
                        ).first()
                        if record:
                            record.tempo, record.nome, record.data = tempo, nome, data
                            aggiornati += 1
                        else:
                            db.session.add(RecordSocietario(
                                sesso=sesso, vasca=VASCA, stile=stile, distanza=distanza, categoria=categoria,
                                tempo=tempo, nome=nome, data=data,
                            ))
                            creati += 1
        db.session.commit()
        print(f"Record importati: {creati} creati, {aggiornati} aggiornati.")


if __name__ == "__main__":
    importa()
