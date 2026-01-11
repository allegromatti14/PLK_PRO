#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aktualizuje matches.json z plk.pl/terminarz (ORLEN Basket Liga 2025/2026)."""

from __future__ import annotations
import json, re
from datetime import datetime
from typing import Optional, Dict, Any, List

import requests
from bs4 import BeautifulSoup

URL = "https://plk.pl/terminarz"
TZ = "+01:00"

def infer_year(month: int) -> int:
    return 2025 if month >= 7 else 2026

def parse_datetime(ddmm: str, hhmm: str) -> str:
    day, month = map(int, ddmm.split("."))
    year = infer_year(month)
    hour, minute = map(int, hhmm.split(":"))
    dt = datetime(year, month, day, hour, minute)
    return dt.isoformat(timespec="minutes") + ":00" + TZ

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def parse_score(line: str) -> Optional[Dict[str,int]]:
    m = re.search(r"(\d{1,3})\s*:\s*(\d{1,3})", line)
    if not m:
        return None
    return {"home": int(m.group(1)), "away": int(m.group(2))}

def main():
    r = requests.get(URL, timeout=30, headers={"User-Agent": "MatiPLK-bot/1.0 (+GitHub Actions)"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    blocks = re.split(r"\n####\s+(\d+)\s+kolejka\s*\n", text)
    matches: List[Dict[str,Any]] = []

    for i in range(1, len(blocks), 2):
        round_no = int(blocks[i])
        block = blocks[i+1]
        lines = block.split("\n")

        for idx, line in enumerate(lines):
            mdt = re.search(r"(\d{2}\.\d{2})/\s*(\d{2}:\d{2})", line)
            if not mdt:
                continue

            ddmm, hhmm = mdt.group(1), mdt.group(2)
            home = clean(lines[idx-2] if idx-2 >= 0 else "")
            away = clean(lines[idx-1] if idx-1 >= 0 else "")
            if not home or not away:
                continue

            start = parse_datetime(ddmm, hhmm)

            tv = None
            for j in range(idx+1, min(idx+6, len(lines))):
                if "Polsat" in lines[j] or "YouTube" in lines[j] or "emocje" in lines[j].lower():
                    tv = lines[j]
                    break

            score = None
            for j in range(idx+1, min(idx+10, len(lines))):
                sc = parse_score(lines[j])
                if sc:
                    score = sc
                    break

            status = "played" if score else "scheduled"
            winner = None
            if score:
                winner = home if score["home"] > score["away"] else away

            safe_home = re.sub(r"\W+", "", home)[:12]
            safe_away = re.sub(r"\W+", "", away)[:12]
            match_id = f"{round_no:02d}-{ddmm.replace('.','')}-{safe_home}-{safe_away}"

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
