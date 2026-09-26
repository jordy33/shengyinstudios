# Shengyin Studios — Logo

Generator for the **Shengyin Studios** logo (music brand): black background,
the *Salina Swashes ExtraLight Italic* typeface in copper/gold, and an
enclosing circle with a **single opening** on the right, at the height of the
letter band.

Produces two files:

| File | Description |
|---|---|
| `logo.svg` | Vector (source of truth) |
| `logo.png` | 1600×1600 preview, rasterized from the same SVG |

## Requirements

- macOS (Apple Silicon or Intel)
- [Homebrew](https://brew.sh)
- Python **3.10+** (3.12 is used — `uharfbuzz` sets that floor)
- `libcairo` (required by `cairosvg`; only available via brew)

## Setup (once)

```sh
# 1) Python 3.12 and libcairo
brew install python@3.12 cairo

# 2) virtual environment
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
source .venv/bin/activate

# 3) Python dependencies
pip install -r requirements.txt
```

> ⚠️ `cairosvg` requires `libcairo`, the system C library. It **cannot** be
> installed via pip alone — that's why `brew install cairo` is mandatory. With
> Homebrew's Python, no extra environment variables are needed.

## Run

```sh
source .venv/bin/activate   # if not already active
python make_logo.py
```

Expected output:

```
ok -> logo.svg / logo.png  (ancho logotipo 905px, radio 582px)
```

## Layout

- `make_logo.py` — builds and generates the logo
- `requirements.txt` — dependencies (`fonttools`, `uharfbuzz`, `cairosvg`)
- `Salina-SwExtraLightItalic.otf` — font (must sit next to the script)
- `logo.svg` / `logo.png` — generated outputs

## Tuning

Main parameters live at the top of `main()` in `make_logo.py`:

- `size` — logo size (px)
- `slot_deg` — opening angle of the circle (degrees)
- `ring_w` — ring thickness
- `NEGRO`, `COBRE`, `ORO` — color palette
