# VELMORA — The Poster for a Place That Isn't There

[![make.fun](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/farcasteralpha/makefun-poster-place-20261121/rank.svg)](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/farcasteralpha/makefun-poster-place-20261121/reward.svg)](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539)

A make.fun entry for **The Poster for a Place That Isn't There**. `main.py`
(pure Python 3.13 standard library, no network) draws an original travel
poster for **VELMORA** — a fictional lagoon island where the sea rises upward
into the sky as the great Upward Falls — and writes it to
`/output/entry.png` (1024×1024 PNG).

## Run

```sh
python3 main.py
# or: MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
```

The render is fully deterministic: two runs produce byte-identical PNGs.
