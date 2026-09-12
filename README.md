# Gestione Squadra Nuoto

Scheletro applicazione Flask per la gestione di una squadra di nuoto:
allenamenti, presenze, gare/tornei, quote e saldo crediti/debiti, messaggi/comunicazioni.

## Struttura del progetto

```
swim_team_app/
├── app.py              # App factory, route base, comandi CLI
├── config.py           # Configurazione (chiave segreta, DB)
├── extensions.py       # Istanze condivise: db, login_manager
├── models.py           # Modelli: User, Allenamento, Presenza, Gara,
│                        # IscrizioneGara, MovimentoContabile, Messaggio
├── auth.py              # Blueprint login/logout
├── admin.py             # Blueprint area amministratore
├── athlete.py            # Blueprint area atleta
├── templates/           # Template Jinja2 (base, login, admin/*, athlete/*)
├── static/css/style.css # Stile base
├── requirements.txt
└── instance/            # Qui verrà creato il file squadra.db (SQLite)
```

## Avvio in locale

```bash
python -m venv venv
source venv/bin/activate        # su Windows: venv\Scripts\activate
pip install -r requirements.txt

export FLASK_APP=app.py         # su Windows: set FLASK_APP=app.py
flask init-db                   # crea le tabelle
flask create-admin admin unaPasswordSicura --nome Mario --cognome Rossi

flask run
```

Poi apri http://127.0.0.1:5000 ed entra con le credenziali admin create.

## Cosa manca / prossimi passi (da fare con Claude Code)

Questo è uno **scheletro funzionante ma minimale**. Punti su cui lavorare:

1. **Validazione dei form** più robusta (es. con Flask-WTF) e messaggi di errore migliori
2. **Gestione presenze**: oggi il modello `Presenza` esiste ma manca ancora la
   pagina per segnarle allenamento per allenamento
2. **Modifica/cancellazione** di utenti, allenamenti, gare (oggi si può solo creare)
3. **Iscrizione alle gare da parte dell'atleta** (oggi solo l'admin vede le gare;
   manca il flusso "l'atleta si iscrive" collegato a `IscrizioneGara`)
4. **Storico e filtri** (es. presenze per mese, movimenti contabili per periodo)
5. **Notifiche** per nuovi messaggi (badge "non letto")
6. **Sicurezza**: cambiare `SECRET_KEY` in produzione tramite variabile d'ambiente,
   valutare limiti sui tentativi di login
7. **Test automatici** (pytest) per i flussi principali

## Deploy su PythonAnywhere

1. Carica il progetto (via Git o upload zip) nella tua area PythonAnywhere
2. Da una Bash console:
   ```bash
   cd swim_team_app
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   flask --app app.py init-db
   flask --app app.py create-admin admin unaPasswordSicura
   ```
3. Nella sezione **Web** di PythonAnywhere crea una nuova web app:
   - Scegli "Manual configuration" e la versione Python del tuo virtualenv
   - Imposta il percorso del virtualenv (es. `/home/tuonome/swim_team_app/venv`)
   - Modifica il file WSGI generato per puntare alla tua app, aggiungendo:
     ```python
     import sys
     path = '/home/tuonome/swim_team_app'
     if path not in sys.path:
         sys.path.insert(0, path)

     from app import app as application
     ```
4. Imposta la variabile d'ambiente `SECRET_KEY` da pannello "Web" → sezione env vars
   (o direttamente nel file WSGI, meno consigliato)
5. Premi **Reload** sulla web app

Il sito sarà raggiungibile su `tuonome.pythonanywhere.com`.

## Nota sul database

Il progetto usa SQLite per semplicità (nessun servizio esterno da configurare,
compatibile col piano gratuito). Se in futuro il numero di utenti/scritture
cresce molto, si può migrare a MySQL (incluso gratuitamente su PythonAnywhere)
cambiando solo `SQLALCHEMY_DATABASE_URI` in `config.py`.
