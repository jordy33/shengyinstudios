# Shengyin Studios — Logo & Media Kit

Generator suite for the **Shengyin Studios** logo (music brand): black
background, the *Salina Swashes ExtraLight Italic* typeface with a metallic
copper/gold gradient, and an enclosing ring with a **single opening** on the
right, at the height of the letter band.

Two scripts share the same vector logo engine:

| Script | Produces |
|---|---|
| `make_logo.py` | A single 1600×1600 master (`logo.svg` / `logo.png`) |
| `make_media_kit.py` | The full set of sizes required by DistroKid, Spotify for Artists, Apple Music for Artists, YouTube, and social platforms |

Everything is built from real vector data — the font's own glyph outlines
(via `fonttools` + `uharfbuzz` shaping) and a procedurally drawn ring — so
every output file is rendered directly at its target resolution. Nothing is
ever upscaled from a smaller raster, no matter how many sizes you generate.

## Requirements

- macOS (Apple Silicon or Intel)
- [Homebrew](https://brew.sh)
- Python **3.10+** (3.12 is used — `uharfbuzz`'s wheel sets that floor)
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

# single master logo (logo.svg / logo.png)
python make_logo.py

# full media kit (media_kit/…)
python make_media_kit.py
```

Expected output:

```
$ python make_logo.py
ok -> logo.svg / logo.png  (ancho logotipo 905px, radio 582px)

$ python make_media_kit.py
archivo                                             tamaño   nota
----------------------------------------------------------------------------------------------------
distrokid/cover_art_3000x3000.png             3000x3000     DistroKid cover art — min. 3000x3000, ...
distrokid/profile_512x512.png                 512x512       Foto de perfil DistroKid ...
spotify/artist_profile_1500x1500.png          1500x1500     Spotify for Artists — avatar circular, ...
...
ok -> media_kit/  (12 assets, PNG + SVG cada uno)
```

## Layout

```
.
├── make_logo.py                     # single 1600×1600 master logo
├── make_media_kit.py                # full media kit (all platform sizes)
├── requirements.txt                 # fonttools, uharfbuzz, cairosvg, pillow
├── Salina-SwExtraLightItalic.otf    # font (must sit next to both scripts)
├── logo.svg / logo.png              # output of make_logo.py
└── media_kit/                       # output of make_media_kit.py
    ├── distrokid/
    │   ├── cover_art_3000x3000.{svg,png}
    │   └── profile_512x512.{svg,png}
    ├── spotify/
    │   ├── artist_profile_1500x1500.{svg,png}
    │   └── artist_header_2660x1140.{svg,png}
    ├── applemusic/
    │   └── artist_image_2400x2400.{svg,png}
    ├── youtube/
    │   ├── profile_800x800.{svg,png}
    │   └── channel_banner_2560x1440.{svg,png}
    └── social/
        ├── instagram_profile_320x320.{svg,png}
        ├── facebook_profile_320x320.{svg,png}
        ├── tiktok_profile_200x200.{svg,png}
        ├── x_profile_400x400.{svg,png}
        └── x_header_1500x500.{svg,png}
```

## Media kit — sizes generated

Every size is fitted inside the logo's design bounding box with a safety
margin, so nothing gets clipped by a platform's circular crop or hidden
behind overlaid UI (channel names, buttons, etc.).

| Platform | File | Size | Notes |
|---|---|---|---|
| DistroKid | `cover_art_3000x3000.png` | 3000×3000 | Release/cover artwork, minimum required |
| DistroKid | `profile_512x512.png` | 512×512 | Profile picture (propagates to Spotify); DK's own minimum is 250×250 |
| Spotify for Artists | `artist_profile_1500x1500.png` | 1500×1500 | Circular avatar; min. 750×750 — extra margin for the circular crop |
| Spotify for Artists | `artist_header_2660x1140.png` | 2660×1140 | Header banner; logo kept in the upper third (bottom ~35% is covered by UI) |
| Apple Music for Artists | `artist_image_2400x2400.png` | 2400×2400 | Square, **no alpha channel** (Apple rejects images with transparency) |
| YouTube | `profile_800x800.png` | 800×800 | Circular channel avatar |
| YouTube | `channel_banner_2560x1440.png` | 2560×1440 | Logo kept inside the 1546×423 safe area (only region guaranteed visible on all devices) |
| Instagram | `social/instagram_profile_320x320.png` | 320×320 | Circular profile picture |
| Facebook | `social/facebook_profile_320x320.png` | 320×320 | Circular profile picture |
| TikTok | `social/tiktok_profile_200x200.png` | 200×200 | Circular profile picture |
| X (Twitter) | `social/x_profile_400x400.png` | 400×400 | Circular profile picture |
| X (Twitter) | `social/x_header_1500x500.png` | 1500×500 | Header banner |

All PNGs are flattened to plain RGB (no alpha channel) and are well under
every platform's file-size limit. Platform specs can change — worth a quick
check against the live upload forms before a launch.

## How it works (short version)

1. **Shaping** — `uharfbuzz` shapes `"Shengyin Studios"` against the font's
   own `GSUB`/`GPOS` tables, so kerning and swash substitutions are real,
   not approximated.
2. **Outlines** — `fonttools` extracts each glyph's actual vector contour
   (`SVGPathPen`), transformed directly into final canvas coordinates
   (`TransformPen`) rather than via a per-glyph `transform=""` attribute —
   this matters so the metallic gradient (see below) resolves in one shared
   coordinate space instead of each glyph's own tiny local space.
3. **Optical centering** — the word is centered on its real ink bounding
   box (swashes included), not on font-metric formulas or advance width,
   which is what makes it sit visually centered inside the ring.
4. **Metallic gradient** — the ring and the letters each get their own
   5-stop linear gradient (shadow → base color → highlight → base color →
   shadow), sized to their own extent but sharing the same light direction,
   to read as brushed copper/gold instead of flat color.
5. **Rendering** — `cairosvg` rasterizes the SVG to PNG at the exact target
   resolution for each output, using the same paths as the `.svg` (source
   of truth).

## Tuning

**`make_logo.py`** — parameters live at the top of `main()`:

- `size` — logo size (px)
- `slot_deg` — opening angle of the ring (degrees)
- `ring_w` — ring thickness
- `NEGRO`, `COBRE`, `ORO` — color palette

**`make_media_kit.py`** — shared logo geometry lives in `LogoDesign`
(`RING_GAP_DEG`, `RING_W_RATIO`, `RING_MARGIN_RATIO`); per-output sizing and
safe-area margins live in the `SPECS` list at the bottom of the file. To add
a new platform/size, add one line to `SPECS` with its canvas size and the
box the logo should fit inside.

Both scripts pull color/gradient intensity from the same `lighten()` /
`darken()` helpers — adjust the blend amount there to make the metal look
brighter or more subdued.
