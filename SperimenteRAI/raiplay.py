#!/usr/bin/env python3
"""
RaiPlay CLI - Esplora il catalogo RaiPlay dalla riga di comando
"""

import argparse
import json
import sys
from pathlib import Path

# Default JSON file path (same directory as script)
DEFAULT_JSON = Path(__file__).parent / "rai.json"


def load_data(filepath):
    """Load and return the RaiPlay JSON data."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Errore: File non trovato: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Errore: JSON non valido: {e}")
        sys.exit(1)


def get_all_items(data):
    """Extract all items from all sections."""
    items = []
    for blocco in data.get('blocchi', []):
        sezione = blocco.get('name', 'Sconosciuto')
        for item in blocco.get('lanci', []):
            item['_sezione'] = sezione  # Add section info to item
            items.append(item)
    return items


def get_all_genres(data):
    """Extract all unique genres from the catalog."""
    genres = set()
    for item in get_all_items(data):
        # Check in isPartOf.generi
        is_part_of = item.get('isPartOf', {})
        for genere in is_part_of.get('generi', []):
            if nome := genere.get('nome'):
                genres.add(nome)
        # Check in isPartOf.sottogenere
        for sottogenere in is_part_of.get('sottogenere', []):
            if nome := sottogenere.get('nome'):
                genres.add(nome)
    return sorted(genres)


def get_all_types(data):
    """Extract all unique content types (tipologia)."""
    types = set()
    for item in get_all_items(data):
        is_part_of = item.get('isPartOf', {})
        for tipologia in is_part_of.get('tipologia', []):
            if nome := tipologia.get('nome'):
                types.add(nome)
    return sorted(types)


def format_item_short(item):
    """Format an item for list display."""
    name = item.get('name', 'N/A')
    sezione = item.get('_sezione', '')
    subtitle = item.get('subtitle', '')

    # Get type from isPartOf
    tipo = ''
    is_part_of = item.get('isPartOf', {})
    tipologie = is_part_of.get('tipologia', [])
    if tipologie:
        tipo = tipologie[0].get('nome', '')

    output = f"  \033[1m{name}\033[0m"
    if tipo:
        output += f"  \033[90m[{tipo}]\033[0m"
    if subtitle and subtitle != name:
        # Truncate long subtitles
        if len(subtitle) > 80:
            subtitle = subtitle[:77] + "..."
        output += f"\n    \033[3m{subtitle}\033[0m"

    return output


def format_item_detail(item):
    """Format an item with full details."""
    lines = []

    name = item.get('name', 'N/A')
    lines.append(f"\033[1;36m{'='*60}\033[0m")
    lines.append(f"\033[1;33m{name}\033[0m")
    lines.append(f"\033[1;36m{'='*60}\033[0m")

    # Section
    if sezione := item.get('_sezione'):
        lines.append(f"\033[1mSezione:\033[0m {sezione}")

    # Subtitle/Description
    if subtitle := item.get('subtitle'):
        lines.append(f"\033[1mSottotitolo:\033[0m {subtitle}")

    is_part_of = item.get('isPartOf', {})

    # Description (from isPartOf)
    if desc := is_part_of.get('description'):
        lines.append(f"\033[1mDescrizione:\033[0m {desc}")

    # Type
    tipologie = is_part_of.get('tipologia', [])
    if tipologie:
        tipos = ', '.join(t.get('nome', '') for t in tipologie)
        lines.append(f"\033[1mTipologia:\033[0m {tipos}")

    # Genres
    generi = is_part_of.get('generi', [])
    if generi:
        genres = ', '.join(g.get('nome', '') for g in generi)
        lines.append(f"\033[1mGeneri:\033[0m {genres}")

    # Subgenres
    sottogeneri = is_part_of.get('sottogenere', [])
    if sottogeneri:
        subgenres = ', '.join(s.get('nome', '') for s in sottogeneri)
        lines.append(f"\033[1mSottogeneri:\033[0m {subgenres}")

    # Year
    if anno := is_part_of.get('anno'):
        lines.append(f"\033[1mAnno:\033[0m {anno}")

    # Channel
    if channel := is_part_of.get('channel'):
        lines.append(f"\033[1mCanale:\033[0m {channel}")

    # Director
    if regia := is_part_of.get('regia'):
        lines.append(f"\033[1mRegia:\033[0m {regia}")

    # Cast
    if interpreti := is_part_of.get('interpreti'):
        lines.append(f"\033[1mInterpreti:\033[0m {interpreti}")

    # Host
    if conduttore := is_part_of.get('conduttore'):
        lines.append(f"\033[1mConduttore:\033[0m {conduttore}")

    # Country
    if country := is_part_of.get('country'):
        lines.append(f"\033[1mPaese:\033[0m {country}")

    # Duration
    if durata := is_part_of.get('durataFirstItem'):
        lines.append(f"\033[1mDurata:\033[0m {durata}")

    # Web link
    if weblink := is_part_of.get('weblink'):
        lines.append(f"\033[1mLink:\033[0m https://www.raiplay.it{weblink}")

    return '\n'.join(lines)


def cmd_sezioni(data, args):
    """List all sections."""
    print("\033[1;32mSezioni disponibili:\033[0m\n")
    for blocco in data.get('blocchi', []):
        name = blocco.get('name', 'Sconosciuto')
        tipo = blocco.get('type', 'N/A')
        count = len(blocco.get('lanci', []))
        print(f"  \033[1m{name}\033[0m \033[90m({count} elementi, tipo: {tipo})\033[0m")
    print()


def cmd_generi(data, args):
    """List all genres."""
    print("\033[1;32mGeneri disponibili:\033[0m\n")
    for genre in get_all_genres(data):
        print(f"  {genre}")
    print()


def cmd_tipologie(data, args):
    """List all content types."""
    print("\033[1;32mTipologie disponibili:\033[0m\n")
    for tipo in get_all_types(data):
        print(f"  {tipo}")
    print()


def cmd_search(data, args):
    """Search and filter items."""
    items = get_all_items(data)
    results = items

    # Filter by section
    if args.sezione:
        sezione_lower = args.sezione.lower()
        results = [i for i in results if sezione_lower in i.get('_sezione', '').lower()]

    # Filter by title
    if args.titolo:
        titolo_lower = args.titolo.lower()
        results = [i for i in results if titolo_lower in i.get('name', '').lower()]

    # Filter by genre
    if args.genere:
        genere_lower = args.genere.lower()
        filtered = []
        for item in results:
            is_part_of = item.get('isPartOf', {})
            # Check generi
            for g in is_part_of.get('generi', []):
                if genere_lower in g.get('nome', '').lower():
                    filtered.append(item)
                    break
            else:
                # Check sottogenere
                for s in is_part_of.get('sottogenere', []):
                    if genere_lower in s.get('nome', '').lower():
                        filtered.append(item)
                        break
        results = filtered

    # Filter by type (tipologia)
    if args.tipo:
        tipo_lower = args.tipo.lower()
        filtered = []
        for item in results:
            is_part_of = item.get('isPartOf', {})
            for t in is_part_of.get('tipologia', []):
                if tipo_lower in t.get('nome', '').lower():
                    filtered.append(item)
                    break
        results = filtered

    # Filter by year
    if args.anno:
        filtered = []
        for item in results:
            is_part_of = item.get('isPartOf', {})
            if args.anno in is_part_of.get('anno', ''):
                filtered.append(item)
        results = filtered

    if not results:
        print("\033[33mNessun risultato trovato.\033[0m")
        return

    print(f"\033[1;32mTrovati {len(results)} risultati:\033[0m\n")

    # Show detailed view for single result or if --dettagli is set
    if len(results) == 1 or args.dettagli:
        for item in results:
            print(format_item_detail(item))
            print()
    else:
        for item in results:
            print(format_item_short(item))
            print()


def cmd_casuale(data, args):
    """Show a random item from the catalog."""
    import random
    items = get_all_items(data)
    if items:
        item = random.choice(items)
        print("\033[1;32mSuggerimento casuale:\033[0m\n")
        print(format_item_detail(item))
    else:
        print("Nessun elemento nel catalogo.")


def cmd_stats(data, args):
    """Show catalog statistics."""
    items = get_all_items(data)
    genres = get_all_genres(data)
    types = get_all_types(data)
    sections = data.get('blocchi', [])

    print("\033[1;32mStatistiche catalogo RaiPlay:\033[0m\n")
    print(f"  \033[1mTotale elementi:\033[0m {len(items)}")
    print(f"  \033[1mSezioni:\033[0m {len(sections)}")
    print(f"  \033[1mGeneri:\033[0m {len(genres)}")
    print(f"  \033[1mTipologie:\033[0m {len(types)}")

    # Count by type
    print(f"\n  \033[1mElementi per tipologia:\033[0m")
    type_counts = {}
    for item in items:
        is_part_of = item.get('isPartOf', {})
        for t in is_part_of.get('tipologia', []):
            nome = t.get('nome', 'Altro')
            type_counts[nome] = type_counts.get(nome, 0) + 1

    for tipo, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {tipo}: {count}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='RaiPlay CLI - Esplora il catalogo RaiPlay',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  %(prog)s --sezioni                     # Mostra tutte le sezioni
  %(prog)s --titolo "medici"             # Cerca per titolo
  %(prog)s --genere "fiction"            # Cerca per genere
  %(prog)s --sezione "Documentari"       # Mostra contenuti di una sezione
  %(prog)s --tipo "Film"                 # Filtra per tipologia
  %(prog)s --titolo "peppa" --dettagli   # Mostra dettagli completi
  %(prog)s --casuale                     # Suggerimento casuale
  %(prog)s --stats                       # Statistiche del catalogo
        """
    )

    parser.add_argument('--file', '-f', default=DEFAULT_JSON,
                        help='Percorso del file JSON (default: rai.json)')

    # List commands
    parser.add_argument('--sezioni', action='store_true',
                        help='Mostra tutte le sezioni disponibili')
    parser.add_argument('--generi', action='store_true',
                        help='Mostra tutti i generi disponibili')
    parser.add_argument('--tipologie', action='store_true',
                        help='Mostra tutte le tipologie disponibili')
    parser.add_argument('--stats', action='store_true',
                        help='Mostra statistiche del catalogo')
    parser.add_argument('--casuale', action='store_true',
                        help='Mostra un elemento casuale')

    # Search/filter options
    parser.add_argument('--sezione', '-s', metavar='NOME',
                        help='Filtra per sezione')
    parser.add_argument('--titolo', '-t', metavar='TESTO',
                        help='Cerca nel titolo')
    parser.add_argument('--genere', '-g', metavar='GENERE',
                        help='Filtra per genere')
    parser.add_argument('--tipo', metavar='TIPO',
                        help='Filtra per tipologia (es: Film, Fiction, Documentari)')
    parser.add_argument('--anno', '-a', metavar='ANNO',
                        help='Filtra per anno')

    # Output options
    parser.add_argument('--dettagli', '-d', action='store_true',
                        help='Mostra dettagli completi per ogni risultato')

    args = parser.parse_args()

    # Load data
    data = load_data(args.file)

    # Execute commands
    if args.sezioni:
        cmd_sezioni(data, args)
    elif args.generi:
        cmd_generi(data, args)
    elif args.tipologie:
        cmd_tipologie(data, args)
    elif args.stats:
        cmd_stats(data, args)
    elif args.casuale:
        cmd_casuale(data, args)
    elif any([args.sezione, args.titolo, args.genere, args.tipo, args.anno]):
        cmd_search(data, args)
    else:
        # Default: show help
        parser.print_help()


if __name__ == '__main__':
    main()
