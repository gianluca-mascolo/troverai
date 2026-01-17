# TroveRAI

**TroveRAI** è uno strumento da riga di comando per consultare la programmazione TV della RAI.

## Requisiti

- Python >= 3.10
- Poetry (per la gestione delle dipendenze)
- Un account RaiPlay valido

## Installazione

```bash
git clone https://github.com/gianluca-mascolo/troverai.git
cd troverai
poetry install
```

## Autenticazione

Prima di utilizzare TroveRAI è necessario autenticarsi con le proprie credenziali RaiPlay.

1. Crea un file `.env` nella cartella del progetto:
```
RAIPLAY_USERNAME="tua.email@esempio.com"
RAIPLAY_PASSWORD="tuapassword"
```

2. Esegui lo script di autenticazione:
```bash
python SperimenteRAI/raiplay_auth.py --login
```

Questo creerà un file `raiplay_tokens.json` con i token di accesso.

## Utilizzo

### Cosa c'è in onda adesso

```bash
poetry run troverai --ora
```

### Palinsesto di un canale

```bash
# Palinsesto di oggi
poetry run troverai --canale rai-1

# Palinsesto di domani
poetry run troverai --canale rai-2 --data domani

# Palinsesto serale (dalle 20:00)
poetry run troverai --canale rai-3 --dalle 20:00
```

### Prima serata

Mostra la programmazione serale (20:00-23:00) dei canali principali:

```bash
poetry run troverai --prima-serata
```

### Ricerca programmi

```bash
poetry run troverai --cerca "film"
poetry run troverai --cerca "TG" --data domani
```

### Lista canali disponibili

```bash
poetry run troverai --canali
```

## Opzioni

| Opzione | Abbreviazione | Descrizione |
|---------|---------------|-------------|
| `--ora` | `-o` | Mostra cosa è in onda adesso |
| `--canale NOME` | `-c NOME` | Palinsesto di un canale specifico |
| `--canali` | | Lista dei canali disponibili |
| `--prima-serata` | `-p` | Prima serata su Rai 1/2/3 |
| `--cerca TESTO` | `-s TESTO` | Cerca un programma per nome |
| `--data DATA` | `-d DATA` | Data (oggi/domani/ieri/dd-mm-yyyy) |
| `--dalle HH:MM` | | Filtra programmi a partire da un orario |
| `--alle HH:MM` | | Filtra programmi fino a un orario |
| `--compatto` | | Formato di output compatto |
| `--json` | | Output in formato JSON (dati API grezzi) |

## Formati data supportati

- `oggi`, `today` - data odierna
- `domani`, `tomorrow` - giorno successivo
- `ieri`, `yesterday` - giorno precedente
- `dd-mm-yyyy` o `dd/mm/yyyy` - data specifica
- `+1`, `-2` - offset rispetto a oggi

## Disabilitare i colori

Per disabilitare l'output colorato, imposta la variabile d'ambiente `NO_COLOR`:

```bash
NO_COLOR=1 poetry run troverai --ora
```

## Output JSON

Con il flag `--json` è possibile ottenere l'output in formato JSON, contenente i dati grezzi delle API RaiPlay senza alcuna semplificazione o filtro.

```bash
# Palinsesto completo in JSON
poetry run troverai --canale rai-1 --json

# Programmi in onda adesso in JSON
poetry run troverai --ora --json

# Lista canali in JSON
poetry run troverai --canali --json

# Ricerca in JSON
poetry run troverai --cerca "film" --json
```

L'output JSON può essere elaborato con strumenti come `jq`:

```bash
# Estrai solo i nomi dei programmi in prima serata
poetry run troverai --prima-serata --json | jq '.. | .name? // empty' | head -10
```

## Struttura del progetto

```
troverai/
├── src/troverai/       # Codice sorgente principale
│   ├── cli.py          # Implementazione CLI
│   ├── __main__.py     # Entry point per python -m
│   └── __init__.py     # Metadata del package
├── SperimenteRAI/      # Script sperimentali
│   └── raiplay_auth.py # Autenticazione RaiPlay
├── pyproject.toml      # Configurazione Poetry
└── README.md
```

## Licenza

Questo progetto è distribuito sotto licenza [GPL-3.0-or-later](LICENSE.md).

## Autore

Gianluca Mascolo
