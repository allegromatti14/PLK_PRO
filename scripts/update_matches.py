#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MatiPLK – aktualizacja matches.json z plk.pl/terminarz

Robi 2 rzeczy:
1) Zbiera CAŁY terminarz (kolejki 1–30) ze strony plk.pl/terminarz
2) Jeśli mecz ma wynik, wpisuje status=played, score i winner.

To jest parser odporny na układ HTML (bazuje na tekście).
"""

from __future__ import annotations
import json, re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

URL = "https://plk.pl/terminarz"
TZ = "+01:00"  # wystarczy do wyświetlania w apce

def infer_year(month: int) -> int:
    # sezon 2025/2026: wrz-gru -> 2025, sty-cze -> 2026
    return 2025 if month >= 7 else 2026

def iso_start(ddmm: str, hhmm: str) -> str:
    d, m = map(int, ddmm.split("."))
    y = infer_year(m)
    hh, mm = map(int, hhmm.split(":"))
    dt = datetime(y, m, d, hh, mm)
    return dt.isoformat(timespec="minutes") + ":00" + TZ

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def safe_id_part(s: str) -> str:
    return re.sub(r"\W+", "", s)[:14]

def parse_score(s: str) -> Optional[Dict[str,int]]:
    m = re.search(r"(\d{1,3})\s*:\s*(\d{1,3})", s)
    if not m:
        return None
    return {"home": int(m.group(1)), "away": int(m.group(2))}

def main() -> None:
    r = requests.get(URL, timeout=40, headers={"User-Agent":"MatiPLK-bot/1.1 (+GitHub Actions)"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    # Znajdź bloki kolejek: różne warianty nagłówka (np. "#### 14 kolejka")
    # Dopuszczamy brak spacji i różne znaki końca linii.
    round_iter = list(re.finditer(r"####\s*(\d+)\s*kolejka", text))
    if not round_iter:
        raise RuntimeError("Nie znaleziono nagłówków kolejek (#### X kolejka).")

    matches: List[Dict[str,Any]] = []

    for idx, mround in enumerate(round_iter):
        round_no = int(mround.group(1))
        start_pos = mround.end()
        end_pos = round_iter[idx+1].start() if idx+1 < len(round_iter) else len(text)
        block = text[start_pos:end_pos]

        # Wyczyść typowe nagłówki tabeli
        block = block.replace("Gospodarz Gość Data spotkania TV Wynik", " ")

        # Parser meczów: HOME + AWAY + "DD.MM/ HH:MM" + opcjonalne TV + opcjonalny wynik
        # Bazuje na tym, że na stronie zawsze jest data w formacie "dd.mm/ hh:mm"
        pat = re.compile(
            r"(?P<home>[^\n]+)\n(?P<away>[^\n]+)\n(?P<ddmm>\d{2}\.\d{2})/\s*(?P<hhmm>\d{2}:\d{2})"
            r"(?P<tail>(?:\n[^\n]+){0,12})",
            re.MULTILINE
        )

        for mm in pat.finditer(block):
            home = clean(mm.group("home"))
            away = clean(mm.group("away"))
            ddmm = mm.group("ddmm")
            hhmm = mm.group("hhmm")
            tail = mm.group("tail") or ""

            # Odfiltruj śmieci
            if not home or not away:
                continue
            if home.lower().startswith(("gospodarz","gość","gosc")):
                continue

            start_iso = iso_start(ddmm, hhmm)

            # TV: szukaj w ogonie
            tv = None
            tv_m = re.search(r"(Polsat[^\n]*|YouTube[^\n]*|Emocje[^\n]*)", tail, re.IGNORECASE)
            if tv_m:
                tv = clean(tv_m.group(1))

            # Wynik: szukaj w ogonie
            score = parse_score(tail)
            status = "played" if score else "scheduled"
            winner = None
            if score:
                winner = home if score["home"] > score["away"] else away

            match_id = f"{round_no:02d}-{ddmm.replace('.','')}-{safe_id_part(home)}-{safe_id_part(away)}"
            matches.append({
                "id": match_id,
                "round": round_no,
                "home": home,
                "away": away,
                "start": start_iso,
                "tv": tv,
                "status": status,
                "score": score,
                "winner": winner
            })

    payload = {
        "meta": {
            "source": URL,
            "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "count": len(matches)
        },
        "matches": matches
    }

    with open("matches.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
