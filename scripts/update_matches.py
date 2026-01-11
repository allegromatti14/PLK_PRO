#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MatiPLK – aktualizacja matches.json z plk.pl/terminarz (ORLEN Basket Liga 2025/2026)

Parser czyta STRUKTURĘ HTML (nagłówki H4 "X kolejka" + tabela pod spodem).
Nie szuka już '####'.
"""

from __future__ import annotations
import json, re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

URL = "https://plk.pl/terminarz"
TZ = "+01:00"

def infer_year(month: int) -> int:
    return 2025 if month >= 7 else 2026

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def parse_datetime(cell_text: str) -> Optional[str]:
    # formaty: "23.12/ 17:30" albo "11.01 15:30"
    m = re.search(r"(\d{2})\.(\d{2}).*?(\d{2}:\d{2})", cell_text)
    if not m:
        return None
    day = int(m.group(1))
    month = int(m.group(2))
    hhmm = m.group(3)
    year = infer_year(month)
    dt = datetime(year, month, day, int(hhmm[:2]), int(hhmm[3:]))
    return dt.isoformat(timespec="minutes") + ":00" + TZ

def parse_score(s: str) -> Optional[Dict[str,int]]:
    m = re.search(r"(\d{1,3})\s*:\s*(\d{1,3})", s)
    if not m:
        return None
    return {"home": int(m.group(1)), "away": int(m.group(2))}

def safe_id_part(s: str) -> str:
    return re.sub(r"\W+", "", s)[:14]

def tv_from_cell(td) -> Optional[str]:
    alts = []
    for img in td.find_all("img"):
        alt = clean(img.get("alt") or "")
        if alt and alt.lower() != "image":
            alts.append(alt)
    text = clean(td.get_text(" ", strip=True))
    if alts:
        return " / ".join(alts)
    if text:
        return text
    return None

def main() -> None:
    r = requests.get(URL, timeout=40, headers={"User-Agent":"MatiPLK-bot/1.2 (+GitHub Actions)"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    rounds = []
    for h in soup.find_all("h4"):
        t = clean(h.get_text(" ", strip=True))
        m = re.match(r"(\d+)\s*kolejka", t, re.IGNORECASE)
        if m:
            rounds.append((int(m.group(1)), h))

    if not rounds:
        raise RuntimeError("Nie znaleziono nagłówków H4 typu 'X kolejka'.")

    matches: List[Dict[str,Any]] = []

    for round_no, h in rounds:
        table = h.find_next("table")
        if not table:
            continue
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            home = clean(tds[0].get_text(" ", strip=True))
            away = clean(tds[1].get_text(" ", strip=True))
            dt_text = clean(tds[2].get_text(" ", strip=True))
            start = parse_datetime(dt_text)

            if not home or not away or not start:
                continue

            tv = tv_from_cell(tds[3]) if len(tds) >= 4 else None
            score_text = clean(tds[4].get_text(" ", strip=True)) if len(tds) >= 5 else ""
            score = parse_score(score_text)
            status = "played" if score else "scheduled"
            winner = None
            if score:
                winner = home if score["home"] > score["away"] else away

            match_id = f"{round_no:02d}-{dt_text.replace(' ','').replace('/','').replace('.','')}-{safe_id_part(home)}-{safe_id_part(away)}"
            matches.append({
                "id": match_id,
                "round": round_no,
                "home": home,
                "away": away,
                "start": start,
                "tv": tv,
                "status": status,
                "score": score,
                "winner": winner
            })

    payload = {
        "meta": {"source": URL, "updated_at": datetime.utcnow().isoformat(timespec="seconds")+"Z", "count": len(matches)},
        "matches": matches
    }

    with open("matches.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
