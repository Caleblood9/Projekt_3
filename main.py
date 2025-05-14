import os
import requests
from bs4 import BeautifulSoup
import csv
import argparse
from urllib.parse import urlparse
from tqdm import tqdm
import json
import re

COLUMNS = {
    "REGISTERED": 3,
    "ENVELOPES": 4,
    "VALID_VOTES": 7
}


def parse_number(text):
    """Převádí textovou reprezentaci čísla s mezerami na int."""
    return int(text.replace('\xa0', '').strip()) if text.strip() else 0


def stahni_html(url):
    """
    Stáhne HTML obsah stránky a vrátí jej jako BeautifulSoup objekt.
    """
    response = requests.get(url, timeout=10)
    response.encoding = 'utf-8'
    return BeautifulSoup(response.text, 'html.parser')


def ziskej_kraj_a_okres(soup):
    """
    Získá název kraje a okresu z HTML stránky.
    """
    kraj = "neznámý kraj"
    okres = "neznámý okres"
    
    for h3 in soup.find_all('h3'):
        text = h3.text.strip()
        if 'Kraj:' in text:
            kraj = text.replace('Kraj:', '').strip()
        elif 'Okres:' in text:
            okres = text.replace('Okres:', '').strip()
    
    if kraj != "neznámý kraj" and okres != "neznámý okres":
        return kraj, okres
        
    for elem_type in ['div', 'span', 'p', 'h2', 'h1', 'td']:
        for tag in soup.find_all(elem_type):
            text = tag.text.strip()
            if 'Kraj:' in text and kraj == "neznámý kraj":
                kraj = text.split('Kraj:')[1].split('\n')[0].strip()
            if 'Okres:' in text and okres == "neznámý okres":
                okres = text.split('Okres:')[1].split('\n')[0].strip()
    
    kraj = re.sub(r'<[^>]+>', '', kraj)
    okres = re.sub(r'<[^>]+>', '', okres)
    
    return kraj, okres


def ziskej_odkazy_obci(soup, base_url):
    """
    Získá seznam obcí z hlavní stránky:
    1. Najde odkazy na detailní stránky obcí
    2. Vrací seznam trojic (kód, název, URL)
    """
    odkazy = []
    radky = soup.select('td.cislo a')
    for a in radky:
        href = a['href']
        code = a.text.strip()
        name = a.find_parent('tr').find_all('td')[1].text.strip()
        full_url = base_url + href
        odkazy.append((code, name, full_url))
    return odkazy


def ziskej_data_obce(code, name, detail_url, cache=None):
    """
    Získá volební data obce:
    1. Pokud existuje cache, vrátí uložená data
    2. Jinak načte statistiky a výsledky stran z webu
    """
    if cache is not None and code in cache:
        return cache[code]

    soup = stahni_html(detail_url)
    tds = soup.select('td')

    try:
        registered = parse_number(tds[COLUMNS["REGISTERED"]].text)
        envelopes = parse_number(tds[COLUMNS["ENVELOPES"]].text)
        valid = parse_number(tds[COLUMNS["VALID_VOTES"]].text)
    except IndexError:
        print(f"Chyba: Struktura tabulky pro obec {name} (kód {code}) neodpovídá očekávání.")
        registered, envelopes, valid = 0, 0, 0
    except ValueError:
        print(f"Chyba: Nelze převést hodnoty na čísla u obce {name} (kód {code}).")
        registered, envelopes, valid = 0, 0, 0

    party_results = {}
    try:
        party_table = soup.find_all("table")[1]
        rows = party_table.find_all("tr")[2:]

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                party = cols[1].text.strip()
                votes_text = cols[2].text.strip()
                party_results[party] = parse_number(votes_text)
    except (IndexError, ValueError):
        pass

    data = {
        "code": code,
        "location": name,
        "registered": registered,
        "envelopes": envelopes,
        "valid": valid,
        **party_results
    }

    if cache is not None:
        cache[code] = data

    return data


def validuj_url(url):
    """
    Validuje URL adresu:
    1. Musí začínat http:// nebo https://
    2. Musí mít platnou strukturu (scheme + netloc)
    3. Musí být dostupná (status < 400)
    """
    if not url.startswith(("http://", "https://")):
        print("Chyba: URL musí začínat http:// nebo https://.")
        return False

    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            print("Chyba: Neplatná URL adresa.")
            return False

        response = requests.head(url, timeout=5)
        return response.status_code < 400
    except Exception as e:
        print(f"Chyba při ověřování URL: {e}")
        return False


def validuj_vystupni_soubor(filename, force=False):
    """
    Validuje název výstupního souboru:
    1. Pokud nemá příponu .csv, automaticky ji opraví
    2. Ověří, zda lze do souboru zapisovat
    3. Upozorní, pokud soubor již existuje
    """
    if not filename.lower().endswith('.csv'):
        corrected = os.path.splitext(filename)[0] + ".csv"
        print(f"⚠️ Upozornění: Opravuji příponu na .csv → {corrected}")
        filename = corrected
    
    if os.path.exists(filename) and not force:
        print(f"⚠️ Upozornění: Soubor {filename} již existuje a bude přepsán.")
        odpoved = input("Chcete pokračovat? (a/n): ").strip().lower()
        if odpoved != 'a' and odpoved != 'ano':
            print("Operace zrušena uživatelem.")
            return None
    
    try:
        with open(filename, 'a', encoding='utf-8') as f:
            pass
        return filename
    except Exception as e:
        print(f"Chyba při zápisu do souboru {filename}: {e}")
        return None


def uloz_do_csv(filename, data):
    """
    Uloží získaná volební data do CSV souboru:
    1. Vytvoří hlavičku se základními údaji a názvy stran
    2. Zapíše všechny řádky s výsledky
    """
    zakladni_sloupce = ['code', 'location', 'registered', 'envelopes', 'valid']
    vsechny_strany = sorted({key for row in data for key in row if key not in zakladni_sloupce})
    hlavicka = zakladni_sloupce + vsechny_strany

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=hlavicka)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def uloz_cache(cache, nazev_souboru="cache.json"):
    """
    Uloží cache do JSON souboru.
    """
    try:
        with open(nazev_souboru, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Chyba při ukládání cache: {e}")


def nacti_cache(nazev_souboru="cache.json"):
    """
    Načte cache z JSON souboru, pokud existuje, jinak vrátí prázdný slovník.
    """
    try:
        if os.path.exists(nazev_souboru):
            with open(nazev_souboru, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Chyba při načítání cache: {e}")
    return {}


def zpracuj_region(url, vystup, base_url, use_cache=True):
    """
    Zpracuje zadaný region:
    1. Načte seznam obcí
    2. Stáhne volební data (využije cache, pokud je k dispozici)
    3. Uloží výsledky do CSV souboru a aktualizuje cache
    """
    soup = stahni_html(url)
    
    kraj, okres = ziskej_kraj_a_okres(soup)
    
    obce = ziskej_odkazy_obci(soup, base_url)
    
    if not obce:
        print("❌ Chyba: Nebyly nalezeny žádné obce. Zkontrolujte URL adresu a zkuste to znovu.")
        return
    
    lokalizace = f"{kraj}" if "Praha" in kraj else f"{kraj}, Okres: {okres}"
    print(f"{lokalizace}")
    print(f"Nalezeno {len(obce)} obcí k zpracování.")

    cache = {} if not use_cache else nacti_cache()
    vysledky = []
    for code, name, detail_url in tqdm(obce, desc="Zpracování obcí", unit="obec"):
        data = ziskej_data_obce(code, name, detail_url, cache if use_cache else None)
        vysledky.append(data)

    if not vysledky:
        print("❌ Chyba: Nebyly nalezeny žádné výsledky.")
        return
    
    if all(data["registered"] == 0 for data in vysledky):
        print("⚠️ Upozornění: Všechny obce mají nulové hodnoty registrovaných voličů.")
        print("Možná příčina: Struktura webu se změnila nebo data nejsou dostupná.")
        odpoved = input("Chcete i přesto uložit data? (a/n): ").strip().lower()
        if odpoved != 'a' and odpoved != 'ano':
            print("Operace ukládání zrušena uživatelem.")
            return

    uloz_do_csv(vystup, vysledky)
    if use_cache:
        uloz_cache(cache)
    print(f"\n✅ Hotovo! Výsledky uloženy do souboru: {vystup}")


def main():
    parser = argparse.ArgumentParser(description="Scraper volebních výsledků z volby.cz pro rok 2017.")
    parser.add_argument("url", help="URL hlavní stránky daného regionu")
    parser.add_argument("vystup", help="Název výstupního souboru (.csv)")
    parser.add_argument("--base-url", default="https://www.volby.cz/pls/ps2017nss/",
                   help="Základní URL adresa webu s výsledky")
    parser.add_argument("--force", action="store_true",
                   help="Přepsat existující soubor bez potvrzení")
    parser.add_argument("--no-cache", action="store_true",
                    help="Nepoužívat cache a vždy stahovat data z webu")
    args = parser.parse_args()
    base_url = args.base_url
  
    if not validuj_url(args.url):
        return

    vystup = validuj_vystupni_soubor(args.vystup, args.force)
    if not vystup:
        return

    zpracuj_region(args.url, vystup, base_url, use_cache=not args.no_cache)


if __name__ == "__main__":
    main()