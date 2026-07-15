#!/usr/bin/env python3
"""
Check the "How I Wrote This" podcast RSS feed for episodes that are not yet
listed in _data/hiwt_episodes.yml.

Prints a JSON report to stdout:

    {"new_episodes": [...], "latest_in_data": "30", "feed_count": 32}

Each entry in new_episodes carries the mechanical fields (number, title, date,
duration, url, spotify_id) plus the raw feed description. The editorial fields
(short_title, hosts, thumb, icon, desc) are left for a human or an agent to
fill in, because they require judgment the feed cannot supply.

Exit codes:
    0  no new episodes
    1  error
    2  new episodes found

Usage:
    python3 scripts/hiwt_check_feed.py
    python3 scripts/hiwt_check_feed.py --verify   # sanity-check the data file only
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

FEED_URL = "https://anchor.fm/s/e65a8714/podcast/rss"
SHOW_EMBED_URL = "https://open.spotify.com/embed/show/3LrmMlwz4gh4dV3eVufXvV"
OEMBED_URL = "https://open.spotify.com/oembed?url=https://open.spotify.com/episode/{}"
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "_data", "hiwt_episodes.yml")
ITUNES_NS = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

REQUIRED_FIELDS = ["number", "title", "date", "duration", "hosts", "thumb", "icon", "url", "desc"]
VALID_THUMBS = {"grocery", "ai", "romance", "valuation", "community", "frugality"}

# "Ep. 0 - Trailer" is in the feed but is intentionally not listed on the page.
EXCLUDED_NUMBERS = {"0"}


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse_data_file(path):
    """Minimal parse of the episode YAML. Avoids a PyYAML dependency: the file
    is machine-written with one quoted scalar per line."""
    entries, current = [], None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("- "):
                if current:
                    entries.append(current)
                current = {}
                line = "  " + line[2:]
            m = re.match(r'\s+(\w+):\s*"(.*)"\s*$', line)
            if m and current is not None:
                current[m.group(1)] = m.group(2).replace('\\"', '"').replace("\\\\", "\\")
    if current:
        entries.append(current)
    return entries


def episode_number(title):
    m = re.match(r"\s*Eps?\.?\s*(\d+)", title)
    return m.group(1) if m else None


def duration_to_minutes(text):
    parts = [int(p) for p in text.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    total = h * 60 + m + (1 if s >= 30 else 0)
    return "{} min".format(total)


def pubdate_to_label(text):
    m = re.search(r"(\d{1,2})\s+(\w{3})\s+(\d{4})", text)
    return "{} {}".format(m.group(2), m.group(3)) if m else None


def resolve_spotify_id(expected_title):
    """The RSS feed does not carry open.spotify.com episode IDs, which the embed
    player needs. The show's embed page exposes the most recent episode's ID;
    confirm it matches the episode we expect before trusting it."""
    try:
        page = fetch(SHOW_EMBED_URL)
    except Exception as exc:
        return None, "could not load show embed page: {}".format(exc)
    ids = re.findall(r'"uri":"spotify:episode:([A-Za-z0-9]{22})"', page)
    if not ids:
        return None, "no episode ID found on show embed page"
    sid = ids[0]
    try:
        meta = json.loads(fetch(OEMBED_URL.format(sid)))
    except Exception as exc:
        return None, "oEmbed lookup failed for {}: {}".format(sid, exc)
    got = meta.get("title", "")
    if got.strip() != expected_title.strip():
        return None, 'ID {} resolves to "{}", not "{}" -- resolve by hand'.format(sid, got, expected_title)
    return sid, None


def verify_data_file(path):
    entries = parse_data_file(path)
    problems = []
    if not entries:
        problems.append("no episodes parsed")
    for i, e in enumerate(entries):
        where = "entry {} (Ep {})".format(i, e.get("number", "?"))
        for f in REQUIRED_FIELDS:
            if not e.get(f):
                problems.append("{}: missing {}".format(where, f))
        if e.get("thumb") and e["thumb"] not in VALID_THUMBS:
            problems.append("{}: unknown thumb '{}'".format(where, e["thumb"]))
        hosts = (e.get("hosts") or "").split()
        if not hosts or any(h not in ("brett", "karen") for h in hosts):
            problems.append("{}: bad hosts '{}'".format(where, e.get("hosts")))
    # the first entry is the embedded latest episode and drives the hero block
    if entries:
        for f in ("spotify_id", "short_title"):
            if not entries[0].get(f):
                problems.append("first entry must have {} (it renders the embed/hero)".format(f))
    for e in entries[1:]:
        if e.get("spotify_id"):
            problems.append("Ep {}: only the first entry should carry spotify_id".format(e.get("number")))
    return entries, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="validate the data file and exit")
    args = ap.parse_args()

    data_path = os.path.normpath(DATA_FILE)
    entries, problems = verify_data_file(data_path)
    if args.verify:
        for p in problems:
            print("PROBLEM: {}".format(p), file=sys.stderr)
        print("{} episodes, {} problems".format(len(entries), len(problems)))
        return 1 if problems else 0
    if problems:
        print("Data file has problems; fix before adding episodes:", file=sys.stderr)
        for p in problems:
            print("  - {}".format(p), file=sys.stderr)
        return 1

    known = {e["number"] for e in entries if e.get("number")}

    try:
        feed = ET.fromstring(fetch(FEED_URL))
    except Exception as exc:
        print("Could not read feed: {}".format(exc), file=sys.stderr)
        return 1

    new = []
    for item in feed.find("channel").findall("item"):
        title = (item.findtext("title") or "").strip()
        num = episode_number(title)
        if num is None:
            continue  # specials without a number: surfaced below
        if num in known or num in EXCLUDED_NUMBERS:
            continue
        dur = item.findtext("itunes:duration", default="", namespaces=ITUNES_NS)
        rec = {
            "number": num,
            "title": title,
            "feed_title": title,
            "date": pubdate_to_label(item.findtext("pubDate") or ""),
            "duration": duration_to_minutes(dur) if dur else None,
            "raw_duration": dur,
            "url": item.findtext("link"),
            "spotify_id": None,
            "feed_description": re.sub(r"<[^>]+>", " ", item.findtext("description") or "").strip(),
        }
        sid, err = resolve_spotify_id(title)
        rec["spotify_id"] = sid
        if err:
            rec["spotify_id_note"] = err
        else:
            # Prefer the canonical open.spotify.com link; the feed's
            # podcasters.spotify.com URL redirects to creators.spotify.com.
            rec["url"] = "https://open.spotify.com/episode/{}".format(sid)
        new.append(rec)

    unnumbered = [
        (i.findtext("title") or "").strip()
        for i in feed.find("channel").findall("item")
        if episode_number((i.findtext("title") or "")) is None
    ]

    report = {
        "new_episodes": new,
        "latest_in_data": entries[0].get("number") if entries else None,
        "feed_count": len(feed.find("channel").findall("item")),
        "data_count": len(entries),
        "unnumbered_feed_items": unnumbered,
    }
    print(json.dumps(report, indent=2))
    return 2 if new else 0


if __name__ == "__main__":
    sys.exit(main())
