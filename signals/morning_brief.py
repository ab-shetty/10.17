"""Claude "morning brief" for the story days -> shared/briefs.json (pre-generated; the demo makes no live API calls).

For each story day d the script computes the facts an operations manager would have on the morning of d
(data through d-1, forecasts issued on d-1; never the realised outcome), and Claude turns them into a short brief.
Claude writes prose only: every number comes from `facts`, and the prompt forbids numbers that aren't there.

Inputs (all in shared/, read-only):
  2024: daily.json, preds.json, metrics.json, episodes.json (replay_days = story days), emissions.json, news.json
  2021: crisis/wait.json (+ crisis/daily.json if A has published it: anchored / offshore / inbound counts)
Cache:  signals/briefs_cache.json  {year:date: {hash, brief...}}  (a day is re-briefed only when its facts change)
Output: shared/briefs.json        [{year, date, headline, brief, watch, facts, scorer}]
        shared/briefs.mock.json   same shape, template text, with --mock (no API key needed)

Usage (repo root):  python signals/morning_brief.py [--mock] [--rebrief]
Needs ANTHROPIC_API_KEY (or an `ant auth login` profile) unless --mock.
"""
import hashlib
import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared"
CACHE = Path(__file__).parent / "briefs_cache.json"
MODEL = "claude-opus-5-5"
PAUSE_S = 4  # between API calls
FUEL_USD_PER_T = {"2024": 760, "2021": 780}  # pipeline/notes/fuel_prices.md (EIA LA diesel proxy for MGO)
# 2021 story days: the build-up, the Sep 10 published-figure check (wayback_2021.md), the late-Oct peak,
# the Nov 16 queuing-rule change, and the unwind.
STORY_2021 = ["2021-09-10", "2021-09-21", "2021-10-05", "2021-10-24", "2021-11-16", "2021-12-14"]

SYSTEM = """You write the morning brief for a port operations manager at the Ports of Los Angeles and Long Beach.
It is a replay of historical data, not live. You get a JSON object of facts known on the morning of the brief.
Rules:
- Everything in the facts was known by this morning. Never say what happened later.
- Use only numbers that appear in the facts. Do not compute new statistics, invent causes, or name ships or companies.
- Round as a person would (one decimal at most). Say "about" for model estimates.
- Be honest about uncertainty: if how_much_to_trust_each_horizon says there is no detectable difference from the simple rule,
  do not present that horizon's forecast as better than the simple rule.
- Plain English, no jargon, no bullet points, no markdown.
Return headline (at most 10 words), brief (2-4 sentences, at most 75 words) and watch (one sentence: the one thing
to keep an eye on today)."""

SCHEMA = {
    "type": "object",
    "properties": {"headline": {"type": "string"}, "brief": {"type": "string"}, "watch": {"type": "string"}},
    "required": ["headline", "brief", "watch"],
    "additionalProperties": False,
}


def read(name):
    p = SHARED / name
    if not p.exists():
        return None
    return json.loads(re.sub(r"\bNaN\b", "null", p.read_text()))


def prev(d, n=1):
    return (date.fromisoformat(d) - timedelta(days=n)).isoformat()


def r1(x, nd=1):
    return None if x is None else round(float(x), nd)


RULE_NAMES = {"persistence": "tomorrow = today", "ma7": "7-day average", "blend": "blend of today and the 7-day average"}


def rebase(phrase):
    """A's phrases are relative to the issue day (d-1). In a brief for d, that day is "yesterday"."""
    return (phrase.replace(" today", " yesterday").replace(" tomorrow", " today")
            .replace("on the target day", "for the forecast day"))


def facts_2024(d, daily, preds, metrics, emissions, news):
    by = {r["date"]: r for r in daily}
    y, wk = by.get(prev(d)), [by[prev(d, k)]["n_anchored"] for k in range(1, 8) if prev(d, k) in by]
    if not y:
        return None
    issued = prev(d)
    fc = sorted((p for p in preds if p["issued"] == issued), key=lambda p: p["h"])
    reliability = {}
    for h, m in (metrics or {}).items():
        ci = m.get("skill_ci90")
        tie = bool(ci and ci[0] <= 0 <= ci[1])
        reliability[f"day_{h}"] = ("no detectable difference from " if tie else
                                   "better than " if m["skill_pct"] > 0 else "worse than ") + RULE_NAMES.get(m["baseline"], m["baseline"]) + \
                                  f" ({m['skill_pct']:+.1f}% on Oct-Dec 2024 test)"
    em = {r["date"]: r for r in emissions["daily"]}.get(prev(d)) if emissions else None
    recent = [n for n in news if 0 <= (date.fromisoformat(d) - date.fromisoformat(n["date"])).days <= 30]
    return {
        "brief_date": d, "dataset": "2024, normal operations",
        "yesterday": {
            "ships_at_anchor": r1(y["n_anchored"]), "ships_at_berth": r1(y["n_moored"]),
            "seven_day_average_at_anchor": r1(sum(wk) / len(wk)) if wk else None,
            "arrivals": y.get("arrivals_24h"), "departures": y.get("departures_24h"),
            "ships_inbound_within_60nm": r1(y.get("inbound_60nm")),
            "ships_loitering_offshore_within_60nm": r1(y.get("offshore_waiting")),
            "max_wind_kts": r1(y.get("wind_max_kts")),
        },
        "forecast_ships_at_anchor": [{
            "for_date": p["date"], "days_ahead": p["h"], "model": r1(p["pred"]),
            "simple_rule": r1(p["baseline"]), "simple_rule_name": RULE_NAMES.get(p["baseline_name"], p["baseline_name"]),
            "main_reasons": [rebase(f["phrase"]) for f in p["top_features"][:3] if f.get("phrase")] if p["h"] == 1 else None,
        } for p in fc],
        "how_much_to_trust_each_horizon": reliability,  # from the Oct-Dec 2024 test
        "emissions_at_anchor_yesterday": em and {
            "nox_tonnes": r1(em["nox_t"], 2), "fuel_tonnes": r1(em["fuel_t"]),
            "fuel_cost_usd_estimate": round(em["fuel_t"] * FUEL_USD_PER_T["2024"], -2),
            "note": "estimate: POLA inventory method, fuel at about $760/t"},
        "recent_news": [{"date": n["date"], "title": n["title"], "risk_score": n["score"]} for n in recent[-3:]],
    }


def facts_2021(d, wait, cdaily):
    row = {r["date"]: r for r in wait["daily"]}.get(prev(d))  # known the evening before d
    week_ago = {r["date"]: r for r in wait["daily"]}.get(prev(d, 8))
    if not row or row.get("little_wait_d") is None:
        return None
    f = {
        "brief_date": d, "dataset": "2021 container backlog (replay)",
        "container_size_ships_waiting_last_night": row["ships_waiting_eod"],
        "same_figure_one_week_earlier": week_ago and week_ago["ships_waiting_eod"],
        "ships_reaching_a_berth_per_day_last_7_days": r1(row["berths_per_day_7d"]),
        "wait_estimate_for_a_ship_joining_today_days": {
            "ours_queue_divided_by_berthing_rate": r1(row["little_wait_d"]),
            "published_7_day_average_of_recent_berthings": r1(row["reported_wait_7d"]),
        },
        # No track record here: Sep-Oct accuracy is only known in hindsight, and a morning brief can't use it.
        "how_the_published_figure_works": "average wait of ships that reached a berth in the last 7 days, so it looks backward",
        "fuel_price_usd_per_tonne": FUEL_USD_PER_T["2021"],
    }
    if d >= "2021-11-16":
        # The queue is now beyond shore AIS: queue / berthing rate undercounts, so don't hand it to the brief.
        f.pop("wait_estimate_for_a_ship_joining_today_days")
        f.pop("container_size_ships_waiting_last_night")
        f.pop("same_figure_one_week_earlier")
        f["rule_change"] = ("Since Nov 16 2021, container ships are told to wait about 150 nm offshore instead of at the "
                            "anchorage. That is beyond shore AIS range, so we cannot count that queue or estimate its wait.")
        f["published_7_day_average_wait_days"] = r1(row["reported_wait_7d"])
    c = cdaily and {r["date"]: r for r in cdaily}.get(prev(d))
    if c:
        f["yesterday_all_ships"] = {"at_anchor": r1(c.get("n_anchored")), "loitering_offshore_within_60nm": r1(c.get("offshore_waiting")),
                                    "inbound_within_60nm": r1(c.get("inbound_60nm"))}
    return f


def mock_brief(f):
    if "forecast_ships_at_anchor" in f:
        fc = f["forecast_ships_at_anchor"]
        t = fc[0] if fc else None
        return {"headline": f"MOCK: {f['yesterday']['ships_at_anchor']} ships at anchor yesterday",
                "brief": "MOCK brief. " + (f"Today's model forecast is about {t['model']} ships, vs {t['simple_rule']} from the simple rule." if t else ""),
                "watch": "MOCK: run signals/morning_brief.py with an API key for the real brief."}
    w = f.get("wait_estimate_for_a_ship_joining_today_days")
    if not w:
        return {"headline": "MOCK: the queue moved 150 nm offshore",
                "brief": "MOCK brief. " + f["rule_change"],
                "watch": "MOCK: run signals/morning_brief.py with an API key for the real brief."}
    return {"headline": f"MOCK: {f['container_size_ships_waiting_last_night']} container ships waiting",
            "brief": f"MOCK brief. A ship joining today should expect about {w['ours_queue_divided_by_berthing_rate']} days; "
                     f"the published figure says {w['published_7_day_average_of_recent_berthings']}.",
            "watch": "MOCK: run signals/morning_brief.py with an API key for the real brief."}


def claude_brief(client, f):
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": json.dumps(f, indent=1)}],
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"refused: {f['brief_date']}")
    out = json.loads(next(b.text for b in resp.content if b.type == "text"))
    return dict(out, scorer=resp.model)


def main():
    mock, rebrief = "--mock" in sys.argv, "--rebrief" in sys.argv
    days = []
    daily, preds, episodes = read("daily.json"), read("preds.json") or [], read("episodes.json") or []
    if daily:
        args = (daily, preds, read("metrics.json"), read("emissions.json"), read("news.json") or [])
        for d in sorted({d for e in episodes for d in e.get("replay_days", [])}):
            days.append(("2024", d, facts_2024(d, *args)))
    wait = read("crisis/wait.json")
    if wait:
        cdaily = read("crisis/daily.json")
        days += [("2021", d, facts_2021(d, wait, cdaily)) for d in STORY_2021]
    days = [x for x in days if x[2]]

    cache = {} if mock or not CACHE.exists() else json.loads(CACHE.read_text())
    client = None
    rows = []
    for year, d, f in days:
        h = hashlib.sha256(json.dumps(f, sort_keys=True).encode()).hexdigest()[:16]
        key = f"{year}:{d}"
        if mock:
            b = dict(mock_brief(f), scorer="template")
        elif not rebrief and cache.get(key, {}).get("hash") == h:
            b = cache[key]["brief"]
        else:
            if client is None:
                import anthropic
                # The SDK retries 429s with backoff (honouring retry-after); allow more retries than the default 2.
                client = anthropic.Anthropic(max_retries=8)
            elif rows:
                time.sleep(PAUSE_S)  # stay under the per-minute rate limit
            try:
                b = claude_brief(client, f)
            except anthropic.RateLimitError as e:
                # Still limited after the retries: keep what's done; a re-run resumes from the cache.
                print(f"Rate limited on the {year} brief for {d} after retries ({len(rows)} of {len(days)} done).\n"
                      f"API says: {getattr(e, 'message', e)}\n"
                      "Finished briefs are cached; re-run to continue. If none finish, check the account's limits.")
                break
            cache[key] = {"hash": h, "brief": b}
            CACHE.write_text(json.dumps(cache, indent=1))  # save after every brief, so a failure loses nothing
            print(f"{key}  {b['headline']}")
        rows.append(dict(year=year, date=d, headline=b["headline"], brief=b["brief"], watch=b["watch"],
                         facts=f, scorer=b["scorer"]))
    if not rows:  # never publish an empty briefs.json: the UI would prefer it over the mock and show nothing
        print("No briefs generated; shared/briefs.json left unchanged.")
        return
    out = SHARED / ("briefs.mock.json" if mock else "briefs.json")
    out.write_text(json.dumps(rows, indent=1))
    if not mock:
        CACHE.write_text(json.dumps(cache, indent=1))
    print(f"{out}: {len(rows)} briefs ({sum(r['year'] == '2024' for r in rows)} for 2024, "
          f"{sum(r['year'] == '2021' for r in rows)} for 2021)")


if __name__ == "__main__":
    main()
