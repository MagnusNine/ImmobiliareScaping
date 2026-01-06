import time
import json
import re
import random
import os
import tkinter as tk
import sys
import pandas as pd
import undetected_chromedriver as uc
import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

FILE_URLS = "urls.txt"     
FILE_EXCEL = "report_immobiliare.xlsx" 

# RICERCA LINK

def ottieni_configurazione_gui():
    """Crea una finestra per inserire URL e Numero Pagine insieme."""
    root = tk.Tk()
    root.title("Configurazione Scraper")
    root.geometry("400x250")
      
    risultati = {"url": None, "pagine": 1}

    tk.Label(root, text="Incolla URL Ricerca", font=("Arial", 10, "bold")).pack(pady=(20, 5))
    entry_url = tk.Entry(root, width=50)
    entry_url.pack(pady=5)
 
    tk.Label(root, text="Numero di Pagine da scansionare:", font=("Arial", 10)).pack(pady=(15, 5))
    spin_pagine = tk.Spinbox(root, from_=1, to=100, width=10, font=("Arial", 12))
    spin_pagine.pack(pady=5)

    def conferma():
        url = entry_url.get().strip()
        pagine = spin_pagine.get()

        if not url:
            messagebox.showerror("Errore", "Devi inserire un URL!")
            return
        
        if not "immobiliare.it" in url:
            messagebox.showwarning("Attenzione", "L'URL non sembra di Immobiliare.it. Procedo comunque...")

        try:
            num_pagine = int(pagine)
        except ValueError:
            messagebox.showerror("Errore", "Il numero di pagine deve essere un numero intero!")
            return

        risultati["url"] = url
        risultati["pagine"] = num_pagine
        root.destroy() 

    tk.Button(root, text="AVVIA ESTRAZIONE 🚀", command=conferma, bg="#4CAF50", fg="white", font=("Arial", 11, "bold")).pack(pady=20)

    root.mainloop()

    if not risultati["url"]:
        print("❌ Operazione annullata dall'utente.")
        sys.exit()

    return risultati["url"], risultati["pagine"]

def estrai_tutto_il_possibile(html_source):
    urls_finali = set()

    pattern_completi = r'https://www.immobiliare.it/annunci/\d+/'
    urls_finali.update(re.findall(pattern_completi, html_source))

    script_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_source)
    if script_match:
        try:
            data = json.loads(script_match.group(1))
            def cerca_url_nel_json(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == "url" and isinstance(v, str) and "/annunci/" in v:
                            urls_finali.add(v if v.startswith('http') else "https://www.immobiliare.it" + v)
                        else: cerca_url_nel_json(v)
                elif isinstance(obj, list):
                    for item in obj: cerca_url_nel_json(item)
            cerca_url_nel_json(data)
        except: pass
    return urls_finali

def attendi_superamento_captcha(driver, timeout=300):
    print("⏳ [FASE 1] In attesa che il captcha venga risolto (manualmente o automaticamente)...")
    inizio = time.time()
    while time.time() - inizio < timeout:
        elementi = driver.find_elements(By.CSS_SELECTOR, "li.nd-list__item, article")
        if len(elementi) > 0:
            print("✅ Contenuto rilevato! Procedo con l'estrazione...")
            return True
        time.sleep(1)
    return False

def esegui_fase_1_raccolta_url():
    print(f"\n{'='*40}\nAVVIO FASE 1: RACCOLTA URL\n{'='*40}")
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)
    tutti_i_link_globali = set()
    
    try:
        for p in range(1, NUMERO_PAGINE + 1):
            sep = "&" if "?" in BASE_URL else "?"
            url_corrente = f"{BASE_URL}{sep}pag={p}" if p > 1 else BASE_URL
            
            print(f"\n📄 Pagina {p}/{NUMERO_PAGINE} -> {url_corrente}")
            driver.get(url_corrente)
            
            if p == 1:
                if not attendi_superamento_captcha(driver):
                    print("❌ Timeout: captcha non risolto in tempo.")
                    break
            
            for _ in range(3):
                driver.execute_script(f"window.scrollBy(0, {random.randint(400, 800)});")
                time.sleep(random.uniform(0.5, 1.2))

            link_pagina = estrai_tutto_il_possibile(driver.page_source)
            print(f"✅ Link trovati in questa pagina: {len(link_pagina)}")
            tutti_i_link_globali.update(link_pagina)
            
            if p < NUMERO_PAGINE:
                time.sleep(random.uniform(4, 7))

        if tutti_i_link_globali:
            with open(FILE_URLS, "w", encoding="utf-8") as f:
                for link in sorted(list(tutti_i_link_globali)):
                    f.write(link + "\n")
            print(f"\n🚀 FASE 1 COMPLETATA! {len(tutti_i_link_globali)} link salvati in {FILE_URLS}")
            return True
        else:
            print("❌ Nessun link trovato.")
            return False

    finally:
        driver.quit()

# FASE 2: ANALISI SINGOLI ANNUNCI 

def parse_html_dettaglio(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    data = {'URL': url}

    price = None
    selectors = [
        ('div', 'in-detail__mainFeaturesPrice'),
        ('div', 'nd-list__item--price'),
        ('div', 'im-mainFeatures__title'), 
        ('span', 'im-mainFeatures__value'),
        ('div', 'styles_ld-overview__price__QSGQc'), 
        ('div', 'Price_price__mzj0D')
    ]
    for tag, class_name in selectors:
        elem = soup.find(tag, class_=class_name)
        if elem:
            price = elem.get_text(strip=True)
            break
    data['Prezzo'] = price if price else "N/D"

    citta = "N/D"
    indirizzo_completo = "N/D"
    
    location_spans = soup.find_all('span', class_='styles_ld-blockTitle__location__n2mZJ')
    
    if location_spans:
        texts = [span.get_text(strip=True) for span in location_spans]
        if len(texts) > 0:
            citta = texts[0] 
            rest = texts[1:]
            if rest:
                rest.reverse() 
                indirizzo_completo = " - ".join(rest)
            else:
                indirizzo_completo = "Via non specificata"
    else:
        title_loc = soup.find('span', class_='im-location')
        if title_loc:
            full_text = title_loc.get_text(strip=True)
            parts = full_text.split(',')
            if len(parts) > 1:
                citta = parts[-1].strip()
                indirizzo_completo = " - ".join(parts[:-1]).strip()
            else:
                citta = full_text

    data['Città'] = citta
    data['Via & Località'] = indirizzo_completo

    dt_elements = soup.find_all('dt')
    dd_elements = soup.find_all('dd')
    if dt_elements and dd_elements:
        dl_lists = soup.find_all('dl')
        for dl in dl_lists:
            keys = dl.find_all('dt')
            values = dl.find_all('dd')
            if len(keys) == len(values):
                for k, v in zip(keys, values):
                    key_text = k.get_text(strip=True)
                    val_text = v.get_text(strip=True)
                    if key_text and val_text:
                        data[key_text] = val_text

    if len(data) <= 4:
        potential_items = soup.find_all('div', attrs={'class': lambda x: x and 'feature' in x.lower()})
        for item in potential_items:
            text = item.get_text(strip=True, separator=':')
            if ':' in text:
                parts = text.split(':')
                if len(parts) >= 2:
                    data[parts[0].strip()] = parts[1].strip()

    return data

def esegui_fase_2_analisi():
    print(f"\n{'='*40}\nAVVIO FASE 2: ANALISI DETTAGLIATA\n{'='*40}")
    
    if not os.path.exists(FILE_URLS):
        print(f"Errore: Il file {FILE_URLS} non esiste. Fase 1 fallita?")
        return

    with open(FILE_URLS, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print("Nessun URL da analizzare.")
        return

    all_data = []
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)

    try:
        for i, url in enumerate(urls):
            print(f"\n[{i+1}/{len(urls)}] Analisi: {url}")
            try:
                driver.get(url)
                time.sleep(random.uniform(3, 6))

                if "captcha" in driver.current_url or "challenge" in driver.page_source:
                    print("⚠️  BLOCCO RILEVATO! Risolvilo e premi INVIO.")
                    input()
                
                html = driver.page_source
                listing_data = parse_html_dettaglio(html, url)
                
                print(f"   Prezzo: {listing_data.get('Prezzo')}")
                print(f"   Città: {listing_data.get('Città')}")
                print(f"   Indirizzo: {listing_data.get('Via & Località')}")
                
                all_data.append(listing_data)

            except Exception as e:
                print(f"   Errore link: {e}")

    finally:
        driver.quit()

    if all_data:
        df = pd.DataFrame(all_data)
        cols_order = ['URL', 'Prezzo', 'Città', 'Via & Località']
        remaining_cols = [c for c in df.columns if c not in cols_order]
        final_cols = [c for c in (cols_order + remaining_cols) if c in df.columns]
        
        df = df[final_cols]
        df.to_excel(FILE_EXCEL, index=False)
        print(f"\n✅✅ TUTTO FINITO! Report salvato in: {FILE_EXCEL}")
    else:
        print("\nNessun dato raccolto.")

if __name__ == "__main__":
    url_scelto, pagine_scelte = ottieni_configurazione_gui()
    BASE_URL = url_scelto
    NUMERO_PAGINE = pagine_scelte
    print(f"\n⚙️  CONFIGURAZIONE:\n🔗 URL: {BASE_URL}\n📄 PAGINE: {NUMERO_PAGINE}\n")
    # 1. Esegui la ricerca
    successo_fase_1 = esegui_fase_1_raccolta_url()
    
    if successo_fase_1:
        # Pausa di sicurezza tra le due fasi per far riposare il driver/IP
        print("\nAttendo 5 secondi prima di iniziare la fase di analisi...")
        time.sleep(5)
        
        # 2. Esegui l'analisi
        esegui_fase_2_analisi()
    else:
        print("Interrotto: Fase 1 non ha prodotto risultati.")