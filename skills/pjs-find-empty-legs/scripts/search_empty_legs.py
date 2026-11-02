#!/usr/bin/env python3
"""Read-only exact-code search of Private Jet Specialist's public empty-leg feed."""
import argparse
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

FEED_URL = "https://privatejetspecialist.com/api/empty-legs.json"
BOARD_URL = "https://privatejetspecialist.com/live-empty-leg-flights/"
MAX_BYTES = 5 * 1024 * 1024


def iso_date(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
        raise ValueError("Dates must use YYYY-MM-DD")
    return date.fromisoformat(value)


def codes(value):
    if not value:
        return set()
    result = {item.strip().upper() for item in value.split(",")}
    if any(not re.fullmatch(r"[A-Z0-9]{3,4}", item) for item in result):
        raise ValueError("Use comma-separated airport codes, not city names")
    return result


def positive_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def safe_listing_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value):
        return False
    try:
        url = urlsplit(value)
        return (url.scheme == "https" and url.hostname in {"villiers.ai", "www.villiers.ai"}
                and not url.username and not url.password and url.port in (None, 443)
                and url.path.startswith("/empty-legs/") and not url.fragment)
    except ValueError:
        return False


class FeedRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if (target.scheme != "https" or target.hostname not in
                {"privatejetspecialist.com", "www.privatejetspecialist.com"}
                or target.username or target.password or target.port not in (None, 443)):
            raise ValueError("Feed redirected to an unexpected origin")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_feed(input_path=None):
    if input_path:
        with Path(input_path).open("rb") as source:
            raw = source.read(MAX_BYTES + 1)
        source_type = "local_snapshot_not_refreshed"
        retrieved_at = None
    else:
        request = Request(FEED_URL, headers={"Accept": "application/json", "User-Agent": "PrivateJetSpecialistPlugin/1.0"})
        with build_opener(FeedRedirects()).open(request, timeout=20) as response:
            raw = response.read(MAX_BYTES + 1)
        source_type = "live_feed_retrieval"
        retrieved_at = datetime.now(timezone.utc).isoformat()
    if len(raw) > MAX_BYTES:
        raise ValueError("Feed exceeds the 5 MiB size limit")
    rows = json.loads(raw)
    if not isinstance(rows, list):
        raise ValueError("Expected a JSON array; inventory was not checked")
    return rows, source_type, retrieved_at


def search(rows, *, origins=None, destinations=None, date_from=None, date_to=None,
           passengers=None, max_price=None, currency=None, as_of=None, limit=5, sort="date"):
    as_of = as_of or datetime.now(timezone.utc).date()
    start = max(date_from or as_of, as_of)
    end = date_to or date.max
    if date_from and date_to and date_to < date_from:
        raise ValueError("date-to must not precede date-from")
    if passengers is not None and (isinstance(passengers, bool) or not isinstance(passengers, int) or passengers < 1):
        raise ValueError("Passengers must be a positive integer")
    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError("Limit must be between 1 and 50")
    if currency and not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Currency must be a three-letter code")
    if max_price is not None and (not positive_number(max_price) or not currency):
        raise ValueError("A positive max-price requires an explicit currency")
    if sort not in {"date", "price"}:
        raise ValueError("Sort must be date or price")
    matches, pending, seen = [], [], set()
    skipped, duplicates, valid = 0, 0, 0
    for raw in rows:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        try:
            day = iso_date(raw.get("date"))
            origin, destination = raw.get("from"), raw.get("to")
            if (not isinstance(origin, str) or not re.fullmatch(r"[A-Z0-9]{3,4}", origin)
                    or not isinstance(destination, str) or not re.fullmatch(r"[A-Z0-9]{3,4}", destination)
                    or not safe_listing_url(raw.get("url"))):
                raise ValueError("Invalid route or source URL")
        except (ValueError, TypeError):
            skipped += 1
            continue
        valid += 1
        identity = raw.get("id")
        key = (identity if isinstance(identity, str) and identity else raw["url"])
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        if day < start or day > end:
            continue
        if origins and origin not in origins or destinations and destination not in destinations:
            continue
        row_currency = raw.get("currency")
        row_currency = row_currency if isinstance(row_currency, str) and re.fullmatch(r"[A-Z]{3}", row_currency) else None
        amount = raw.get("price")
        amount = amount if positive_number(amount) else None
        capacity = raw.get("capacity")
        capacity = capacity if isinstance(capacity, int) and not isinstance(capacity, bool) and capacity > 0 else None
        uncertainties = []
        if passengers is not None:
            if capacity is None:
                uncertainties.append("capacity_unknown")
            elif capacity < passengers:
                continue
        if currency:
            if row_currency is None:
                uncertainties.append("currency_unknown")
            elif row_currency != currency:
                continue
        if max_price is not None:
            if amount is None:
                uncertainties.append("price_unknown")
            elif row_currency == currency and amount > max_price:
                continue
        aircraft = raw.get("aircraft")
        aircraft = aircraft[:200] if isinstance(aircraft, str) and aircraft.strip() else None
        row = {"id": str(key)[:250], "from": origin, "to": destination, "date": day.isoformat(),
               "aircraft": aircraft, "capacity": capacity, "listed_price": amount,
               "currency": row_currency, "url": raw["url"], "status": "listed_unconfirmed",
               "date_precision": "day", "same_day_time_unverified": day == as_of,
               "filter_uncertainties": uncertainties}
        (pending if uncertainties else matches).append(row)
    if rows and valid == 0:
        raise ValueError("No valid flight records; the feed schema or source URLs may have changed")
    def ordering(row):
        price_key = (row["currency"] or "ZZZ", row["listed_price"] is None, row["listed_price"] or math.inf)
        return (*price_key, row["date"], row["id"]) if sort == "price" else (row["date"], *price_key, row["id"])
    matches.sort(key=ordering)
    pending.sort(key=ordering)
    return {"status": "empty_feed_unverified" if not rows else "matches_found" if matches else "needs_confirmation" if pending else "no_matches_in_source",
            "as_of_date": as_of.isoformat(), "records_read": len(rows), "invalid_records_skipped": skipped,
            "duplicates_skipped": duplicates, "match_count": len(matches), "needs_confirmation_count": len(pending),
            "matches": matches[:limit], "needs_confirmation": pending[:limit],
            "sort": sort, "price_sort_groups_by_currency": True,
            "notice": "Listed whole-aircraft opportunities, not guaranteed availability or bookings. Confirm time, total price, and terms with the operator. Private Jet Specialist may earn a referral commission.",
            "coverage_note": "The compact feed may omit flights shown on the public board.", "board_url": BOARD_URL}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="origin")
    parser.add_argument("--to", dest="destination")
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    parser.add_argument("--as-of", help="Current departure-local date; defaults to today's UTC date")
    parser.add_argument("--passengers", type=int)
    parser.add_argument("--max-price", type=float)
    parser.add_argument("--currency")
    parser.add_argument("--sort", choices=["date", "price"], default="date")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--input", help="Read a local JSON snapshot instead of fetching the public feed")
    args = parser.parse_args()
    try:
        rows, source_type, retrieved_at = read_feed(args.input)
        result = search(rows, origins=codes(args.origin), destinations=codes(args.destination),
                        date_from=iso_date(args.date_from) if args.date_from else None,
                        date_to=iso_date(args.date_to) if args.date_to else None,
                        as_of=iso_date(args.as_of) if args.as_of else None,
                        passengers=args.passengers, max_price=args.max_price,
                        currency=args.currency.upper() if args.currency else None, limit=args.limit, sort=args.sort)
        result.update(source=FEED_URL if not args.input else "local JSON snapshot", source_type=source_type,
                      retrieved_at=retrieved_at, inventory_updated_at=None,
                      as_of_basis="supplied_current_date" if args.as_of else "UTC calendar date")
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as error:
        message = str(error) if isinstance(error, (ValueError, json.JSONDecodeError)) else "Could not read the inventory source; use the public board or a supplied JSON snapshot."
        print(json.dumps({"status": "error", "inventory_checked": False, "message": message, "board_url": BOARD_URL}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
