This directory holds fetched source texts for the `carlo_audit` case. They are gitignored
(we do not redistribute another entrant's content — we point at it).

The sources are the 40 generated evidence briefs from Carlo Martinucci's public FLF entry:
  https://github.com/carlomartinucci/flf-epistack-contest  (evidence/*.md)

We ingest his OUTPUT as our INPUT to audit its evidential independence — which of his
"independent" briefs collapse onto a shared underlying study, and whether his 72% natural /
28% lab bottom line survives a Herfindahl effective-independence correction. This is an
interoperability demonstration, with full attribution; it does not re-adjudicate the origin.

To (re)fetch the raw texts (no API key needed):
  python -m src.fetch --case carlo_audit
  # or re-run the one-off fetch used to build this case (URLs are in ../sources.json)

Then run the pipeline (ingest + structure need ANTHROPIC_API_KEY; assess + concentration
are deterministic and need no key):
  python -m src.run --case carlo_audit
