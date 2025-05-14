# Volební Scraper 2017 (volby.cz)

Python nástroj pro stahování a ukládání volebních výsledků z voleb do Poslanecké sněmovny ČR 2017 (volby.cz).

# Funkce

- Scraping volebních dat z veřejného webu volby.cz
- Podpora cache (zrychlení opakovaného zpracování)
- Možnost vypnout cache pomocí `--no-cache`
- Ukládání výsledků do přehledného `.csv` souboru
- Detekce a validace vstupních URL
- Snadná změna základní URL
- Zobrazení progress baru pro přehled zpracování

# Požadavky

- Python 3.7+
- Knihovny:
  - `requests`
  - `beautifulsoup4`
  - `tqdm`

# Nainstaluj knihovny:
```bash
pip install -r requirements.txt
```

# Návod pro použití:

Ke spuštění potřeba 2 argumentů:
1. url - konkrétní odkaz na obec např. https://www.volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=1&xnumnuts=1100
2. název výstupního souboru např. vysledky.csv (program automaticky dopní .csv pokud není uvedeno)

Volitelné argumenty:
- --force přepíše výstupní soubor bez dotazu
- --no-cache ignoruje uloženou cache a vždy stahuje data z webu
- --base-url možnost přepsání základní URL

Příklad příkazu a výstupu:
```bash
python main.py "https://www.volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=1&xnumnuts=1100" "vysledky_praha.csv"
Hlavní město Praha
Nalezeno 57 obcí k zpracování.
Zpracování obcí: 100%|████████████████████████| 57/57 [00:16<00:00, 3.46 obec/s]

✅ Hotovo! Výsledky uloženy do souboru: vysledky_praha.csv
```

Výstupní soubor přiložen jako ukazka.csv

