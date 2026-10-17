"""Score 2024 port news for anchorage-queue disruption risk with Claude -> shared/news.json.

Input:  signals/sources.json  [{date, title, text, url}]  (hand-collected, every row sourced)
Cache:  signals/scored.json   {url: {score, reason, scorer}}  (re-used unless --rescore)
Output: shared/news.json      [{date, score, title, reason, url}]  (contract in CLAUDE.md)

Usage (repo root):  python signals/score_news.py [--rescore]
Needs ANTHROPIC_API_KEY only for rows missing from the cache (or with --rescore).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
SOURCES = HERE / "sources.json"
CACHE = HERE / "scored.json"
OUT = HERE.parent / "shared" / "news.json"
MODEL = "claude-opus-5-5"

SYSTEM = """You score news for a forecast of how many cargo ships and tankers wait at anchor in San Pedro Bay
(Ports of Los Angeles and Long Beach) over the next 1-3 days to a few weeks.
Score = risk that the item pushes that anchored queue UP, from 0 (no effect, or pushes it down) to 1
(a major, direct disruption such as a West Coast strike or a terminal closure). Volume growth that the
ports report handling without backlog is modest. Indirect events far from Southern California are low.
The reason is one plain sentence, at most 20 words, naming the mechanism."""

SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "number"}, "reason": {"type": "string"}},
    "required": ["score", "reason"],
    "additionalProperties": False,
}


def score(client, item):
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Date: {item['date']}\nTitle: {item['title']}\n{item['text']}"}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"refused: {item['title']}")
    out = json.loads(next(b.text for b in resp.content if b.type == "text"))
    return dict(score=round(min(1.0, max(0.0, float(out["score"]))), 2), reason=out["reason"], scorer=resp.model)


def main():
    rescore = "--rescore" in sys.argv
    items = json.loads(SOURCES.read_text())
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [it for it in items if rescore or it["url"] not in cache]
    if todo:
        import anthropic
        client = anthropic.Anthropic()
        for it in todo:
            cache[it["url"]] = score(client, it)
            print(f"{cache[it['url']]['score']:.2f}  {it['title'][:70]}")
        CACHE.write_text(json.dumps(cache, indent=1))
    rows = [dict(date=it["date"], score=cache[it["url"]]["score"], title=it["title"],
                 reason=cache[it["url"]]["reason"], url=it["url"]) for it in items]
    rows.sort(key=lambda r: r["date"])
    OUT.write_text(json.dumps(rows, indent=1))
    print(f"{OUT}: {len(rows)} rows ({len(todo)} scored now, {len(rows) - len(todo)} from cache)")


if __name__ == "__main__":
    main()
