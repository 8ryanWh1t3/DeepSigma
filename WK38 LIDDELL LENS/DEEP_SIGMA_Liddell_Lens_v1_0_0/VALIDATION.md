# Validation record

Version 1.0.0 · 20 September 2026

- All 14 automated tests passed.
- Python and JavaScript result structures and numeric values agree for all three included examples and 30 seeded varied datasets, within floating-point tolerance.
- Known totals independently checked: the illustrative benefit dataset records 340 baseline and 240 CERPA person-minutes; the overhead dataset records 50 baseline and 70 CERPA person-minutes.
- Zero baselines yield undefined percentages, unfinished or unsupported decisions are excluded from paired timing but retained in overall counts and effort, and excessive numeric ratios fail explicitly.
- Both CLIs protect the input from direct or hardlink overwrite and neutralize formula-like CSV case IDs.
- JavaScript syntax, local asset references, unique HTML IDs, and literal DOM references passed static checks.

Browser rendering and interactive behavior were not exercised in a real browser because the available environment lacked a browser executable. The dashboard uses standard local HTML, CSS, and JavaScript, but this is a remaining validation limitation. The Python and JavaScript calculation engines and both CLIs were executed directly.

These checks verify implementation behavior. They do not validate the effectiveness of Deep Sigma or the indirect approach on real organizational data.
