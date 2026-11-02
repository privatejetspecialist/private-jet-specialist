# Private Jet Specialist

An agent plugin for private jet planning, live empty-leg discovery, and charter quote comparisons. Published by [Private Jet Specialist](https://privatejetspecialist.com/).

## What it does

| Skill | Helps with |
| --- | --- |
| `pjs-find-empty-legs` | Published flight searches by route, date, passengers, and price; exact matches versus alternatives |
| `pjs-plan-charter` | Trip briefs, aircraft needs, indicative estimates, and authorized quote inquiries through the existing site |
| `pjs-compare-charter-quotes` | Comparable prices, aircraft fit, pets/baggage, missing fees, and cancellation/recovery terms |

It helps travelers move toward booking. It does **not** reserve aircraft, accept payment, or confirm a booking. Villiers arranges charters through the linked flow; the named carrier operates the flight. Private Jet Specialist may earn a commission through referral links.

## Example requests

- “Find empty legs from Sarasota or Tampa to New York for four passengers next week.”
- “Prepare a round-trip charter request for four adults, two large dogs, and six suitcases.”
- “Compare these offers and show whether the cheaper empty leg works for my arrival deadline.”

## Use

Install this package in an agent host that supports Agent Plugins 1.0 and skills. Portable skills live under `skills/`; a skill-compatible host can also import those folders individually. For current inventory, the host needs public web access. For optional deterministic filtering, it needs Python 3 and network access or a supplied JSON snapshot. No API key or separate MCP server is included or required. Browser-assisted inquiry submission additionally requires browser access and the traveler's authorization.

```bash
python3 skills/pjs-find-empty-legs/scripts/search_empty_legs.py \
  --from SRQ,TPA,PIE --to TEB,HPN \
  --date-from YYYY-MM-DD --date-to YYYY-MM-DD --passengers 4
```

Replace date placeholders with actual future dates and verify selected airports. Add `--max-price 15000 --currency USD` for a budget. `--input feed.json` searches a supplied snapshot; it is not a live refresh. `--as-of YYYY-MM-DD` sets the current departure-local date for filtering; otherwise today's UTC date is used.

The script makes a read-only GET to the public [compact feed](https://privatejetspecialist.com/api/empty-legs.json). It sends no itinerary, contact details, or booking requests. The [public board](https://privatejetspecialist.com/live-empty-leg-flights/) can include additional opportunities. An empty compact feed can also reflect an upstream retrieval problem, so the skills check the board before concluding there are no matches.

Listed prices are in their original currencies and describe the aircraft, not individual seats. Dates, availability, taxes/fees, pets, baggage, aircraft suitability, and cancellation terms need confirmation. Date-only same-day results need a departure-time check. Private quotes and traveler details are not bundled or published.

## Verification

Run `python3 -m unittest discover -s tests -v` for the filter's deterministic tests. See [validation notes](docs/validation.md) for completed checks and remaining host/directory checks. Native Cursor installation and directory acceptance must be verified separately; package creation does not establish either.
