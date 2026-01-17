# SperimenteRAI

Questa cartella contiene i file di sperimentazione sviluppati durante la creazione di TroveRAI.

This folder contains experimental files developed during the creation of TroveRAI.

## Cronologia dello sviluppo

### Fase 0: Ricerca iniziale (16 Gennaio 2026)

Il progetto è iniziato con una ricerca Google: `rai programmazione json site:rai.it`

Questa ricerca ha portato alla scoperta di endpoint JSON non documentati sul sito RAI contenenti dati del catalogo RaiPlay.

### Fase 1: Correzione JSON (16 Gennaio 2026)

Il file JSON scaricato (`rai.json`) conteneva errori di sintassi. Gli errori erano principalmente **doppie virgole** (`,,`) causate da problemi nel sistema di templating server-side di RAI. Quando un elemento veniva saltato dal template ma il separatore virgola non veniva gestito correttamente, si generavano virgole duplicate.

**Risultato**: Creazione di `jsonfix.py` per correggere errori JSON comuni (doppie virgole, virgole finali, ecc.).

### Fase 2: Tool di interrogazione catalogo (16 Gennaio 2026)

Dopo aver sanificato il JSON, è stato creato uno strumento per interrogare il catalogo RaiPlay con varie opzioni di ricerca.

**Risultato**: Creazione di `raiplay.py` con opzioni come `--categoria`, `--sezione`, `--titolo`, `--genere`.

### Fase 3: Ricerca API (17 Gennaio 2026)

Ricerca di endpoint API ufficiali e non ufficiali per i palinsesti RaiPlay:

- **Web search** ha trovato progetti esistenti:
  - [palinsesto-italia](https://github.com/russhtyy/palinsesto-italia) - API non ufficiale per palinsesti TV
  - [GuidaTV-API](https://github.com/pizidavi/GuidaTV-API) - Altra API non ufficiale

- **Analisi del plugin streamlink** ([raiplay.py di streamlink](https://github.com/streamlink/streamlink/blob/master/src/streamlink/plugins/raiplay.py)) ha rivelato:
  - Endpoint autenticazione: `https://www.raiplay.it/raisso/login/domain/app/social`
  - Domain API Key: `arSgRtwasD324SaA`

### Fase 4: Autenticazione (17 Gennaio 2026)

Sviluppo del sistema di autenticazione per ottenere token JWT validi.

- Creazione di `raiplay_auth.py` per autenticarsi e ottenere token JWT
- Correzione di problemi nel refresh dei token (URL base errato, domainApiKey mancante)
- Il refresh token richiede l'endpoint `https://www.rai.it/` invece di `https://www.raiplay.it/`

**Risultato**: Creazione di `raiplay_auth.py` che gestisce login e refresh dei token.

### Fase 5: CLI Palinsesti TV

Sviluppo dell'interfaccia a riga di comando per consultare i palinsesti TV in tempo reale.

- Creato inizialmente come `raiplay_guida.py`
- Rinominato in `troverai` e ristrutturato come package Python
- Aggiunto supporto per `NO_COLOR`
- Aggiunto output JSON con flag `--json`

**Risultato**: Package `troverai` con struttura `src/` e gestione Poetry.

## File presenti

| File | Descrizione |
|------|-------------|
| `jsonfix.py` | Utility per correggere errori comuni nei file JSON |
| `raiplay.py` | Tool per interrogare il catalogo RaiPlay da file JSON locale |
| `raiplay_auth.py` | Script di autenticazione per ottenere token RaiPlay |
