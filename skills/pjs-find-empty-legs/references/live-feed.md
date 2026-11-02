# Live inventory contract

Verified against the public feed and rendered board on November 2, 2026. Recheck when the response changes.

| Resource | URL | Purpose |
| --- | --- | --- |
| Compact feed | https://privatejetspecialist.com/api/empty-legs.json | Read-only JSON array; no credentials or traveler data |
| Flight board | https://privatejetspecialist.com/live-empty-leg-flights/ | Broader rendered listings and filters |
| Quote flow | https://privatejetspecialist.com/book-private-jet/ | Estimate followed by optional inquiry to Villiers |
| Disclosure | https://privatejetspecialist.com/affiliate-disclosure/ | Publisher relationship |

Each record has `id`, `from`, `to`, `date`, `aircraft`, `price`, `currency`, `capacity`, and `url`. The date is YYYY-MM-DD with no time or zone. Airport codes are generally IATA; the board may show ICAO. Capacity is an aircraft limit, not individual seat inventory. Price is numeric in the stated currency; the record does not prove all taxes/fees are included. Observed links use https://villiers.ai/empty-legs/ with the publisher's `id=ZBCS78` referral.

There is no global generated-at field. Retrieval time is not inventory-confirmation time. The board's update indicator also does not prove operator availability.

Coverage can differ: the verification observation had 359 board opportunities and 279 compact-feed records. These are historical observations, never future counts. Flights without usable identifiers may be absent from the compact feed. Check the board when needed.

Source inspection on November 2, 2026 confirms that the compact feed filters invalid airport identifiers, unparsed prices, missing capacity, and flights it cannot establish as future using airport-local time. It can return an empty array on upstream retrieval failure as well as when no records qualify. Never treat an empty array alone as proof of zero inventory. Check the board for its visible status.

The script sends a GET only, without trip parameters, contact details, or booking requests. Its local-file mode searches a snapshot. Network/schema failures produce errors; an empty array produces `empty_feed_unverified`. Filters use exact airport-code membership and inclusive dates. It does not geocode, translate cities, compute airport radius, verify aircraft performance, or approve pets. Same-day results carry a time-confirmation flag. Unknown capacity/price are separated when required by a filter; malformed rows and unsafe source URLs are excluded.
