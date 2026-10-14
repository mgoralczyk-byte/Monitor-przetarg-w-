import os
import json
import requests
from datetime import datetime

# --- KONFIGURACJA ---
CPV_CODES = ["19520000-7", "18930000-7"]
BASE_DOMAIN = "ezamowienia.gov.pl"
API_URL = f"https://{BASE_DOMAIN}/mo-board/api/v1/notice"
CACHE_FILE = "widziane_przetargi.json"

WEBHOOK_URL = ""

def wczytaj_widziane():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def zapisz_widziane(widziane_ids):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(widziane_ids), f, ensure_ascii=False, indent=2)

def pobierz_ogloszenia(kod_cpv):
    params = {
        "CpvCode": kod_cpv,
        "NoticeType": "ContractNotice",
        "PageSize": 20,
        "SortingOrder": "Descending"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get("items", []) or data.get("notices", []) or []
        return []
    except Exception as e:
        print(f"Blad podczas odpytywania API dla CPV {kod_cpv}: {e}")
        return []

def wyslij_powiadomienie(przetarg):
    bzp_number = przetarg.get("noticeNumber") or przetarg.get("id") or "Brak numeru"
    order_title = przetarg.get("orderObject") or przetarg.get("title") or "Brak tytulu"
    purchaser = przetarg.get("purchaserName") or przetarg.get("organizationName") or "Nieokreslony zamawiajacy"
    submission_date = przetarg.get("submittingOffersDate") or przetarg.get("deadline") or "Brak terminu"
    
    link = f"https://{BASE_DOMAIN}/mo-client-board/bzp/notice-details/{bzp_number}"

    tresc = (
        f"NOWY PRZETARG! (CPV {kod_cpv_val(przetarg)})\n"
        f"Zamawiajacy: {purchaser}\n"
        f"Przedmiot: {order_title}\n"
        f"Termin skladania ofert: {submission_date}\n"
        f"Link: {link}\n"
        f"{'-'*50}"
    )
    print(tresc)

    if WEBHOOK_URL:
        try:
            requests.post(WEBHOOK_URL, json={"content": tresc}, timeout=5)
        except Exception as e:
            print(f"Blad wysylania Webhooka: {e}")

def kod_cpv_val(przetarg):
    return przetarg.get('cpvCode', '19520000-7')

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sprawdzanie nowych przetargów...")
    widziane_ids = wczytaj_widziane()
    nowe_count = 0

    for cpv in CPV_CODES:
        ogloszenia = pobierz_ogloszenia(cpv)
        for p in ogloszenia:
            notice_id = str(p.get("id") or p.get("noticeNumber") or "")
            if notice_id and notice_id not in widziane_ids:
                wyslij_powiadomienie(p)
                widziane_ids.add(notice_id)
                nowe_count += 1

    zapisz_widziane(widziane_ids)
    print(f"Zakres zakończony. Nowe przetargi: {nowe_count}\n")

if __name__ == "__main__":
    main()
