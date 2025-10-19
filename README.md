# Subclip Random Cuts

`randcuts.py` is a small command-line tool for building a single audio file from random
segments of a source track. You provide the source file and a set of desired clip
lengths, and the script stitches together faded clips chosen from random starting
positions.

## Requirements

- Python 3.9 or newer
- [pydub](https://github.com/jiaaro/pydub) (`pip install pydub`)
- A working FFmpeg installation available on your `PATH` (required by pydub for most
  formats)

## Quick start

1. Install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install pydub
   ```

2. Run `randcuts.py`, providing the source file and a list of clip durations in seconds:

   ```bash
   python randcuts.py path/to/source.wav 3.5 1.25 2.0 --out mixed.wav
   ```

   This command loads `source.wav`, extracts three random clips with durations of 3.5,
   1.25, and 2.0 seconds, applies short fade-in/out transitions, and exports the
   concatenated result to `mixed.wav`.

## Usage

```bash
python randcuts.py SRC_PATH DURATION [DURATION ...] [--seed SEED] [--out OUT]
```

- `SRC_PATH` – path to the input audio file.
- `DURATION` – one or more clip lengths (in seconds). Non-positive values are rejected.
- `--seed` – optional integer seed to make the random clip selection reproducible.
- `--out` – output file path. The extension determines the export format (default:
  `out.wav`).

The script prints metadata for each generated clip, including its index, duration,
random start position, and applied fade length.

