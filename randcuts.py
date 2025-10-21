"""Random audio clip concatenation tool."""
from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from pydub import AudioSegment


@dataclass
class ClipMetadata:
    """Metadata describing a generated audio clip."""

    index: int
    duration_ms: int
    start_ms: int
    fade_ms: int


@dataclass
class RandomCutsResult:
    """Result of generating a random set of audio clips."""

    source: AudioSegment
    concatenated: AudioSegment
    metadata: List[ClipMetadata]

    def export(self, output_path: Path | str) -> Path:
        """Export the concatenated audio to ``output_path``.

        Args:
            output_path: Destination file path. The extension determines the
                export format.

        Returns:
            The path the audio was exported to.

        Raises:
            ValueError: If ``output_path`` lacks a file extension.
        """

        path = Path(output_path)
        if not path.suffix:
            raise ValueError("Output path must include a file extension to infer format.")
        export_format = path.suffix.lstrip(".").lower()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.concatenated.export(path, format=export_format)
        return path


class AudioProcessingError(RuntimeError):
    """Raised when audio loading or processing fails."""


def _convert_durations_to_ms(durations: Sequence[float]) -> List[int]:
    """Convert durations in seconds to integer milliseconds with validation."""

    durations_ms: List[int] = []
    for idx, dur in enumerate(durations):
        if dur <= 0:
            raise ValueError(f"Duration at position {idx} must be greater than 0 (got {dur!r}).")
        dur_ms = int(round(dur * 1000))
        if dur_ms <= 0:
            raise ValueError(
                f"Duration at position {idx} is too small after rounding; must be at least 1 ms (got {dur!r})."
            )
        durations_ms.append(dur_ms)
    return durations_ms


def build_random_clips_concatenation(
    source: AudioSegment,
    durations: Sequence[float],
    rng: random.Random,
) -> Tuple[AudioSegment, List[ClipMetadata]]:
    """Construct a concatenated audio segment composed of random clips.

    Args:
        source: The source audio segment to slice clips from.
        durations: Durations of each desired clip, in seconds.
        rng: Random number generator used to pick start positions.

    Returns:
        A tuple of the concatenated audio segment and metadata describing each clip.

    Raises:
        ValueError: If any duration is invalid relative to the source.
    """

    src_ms = len(source)
    durations_ms = _convert_durations_to_ms(durations)

    clips: List[AudioSegment] = []
    metadata: List[ClipMetadata] = []

    for idx, dur_ms in enumerate(durations_ms):
        if dur_ms > src_ms:
            raise ValueError(
                f"Duration at position {idx} ({dur_ms} ms) exceeds source length ({src_ms} ms)."
            )

        max_start = src_ms - dur_ms
        start_ms = rng.randint(0, max_start) if max_start > 0 else 0
        clip = source[start_ms : start_ms + dur_ms]
        fade_ms = min(300, dur_ms // 2)
        if fade_ms > 0:
            clip = clip.fade_in(fade_ms).fade_out(fade_ms)
        clips.append(clip)
        metadata.append(ClipMetadata(index=idx, duration_ms=dur_ms, start_ms=start_ms, fade_ms=fade_ms))

    if not clips:
        concatenated = AudioSegment.silent(duration=0, frame_rate=source.frame_rate)
        concatenated = concatenated.set_channels(source.channels)
    else:
        concatenated = clips[0]
        for clip in clips[1:]:
            concatenated += clip

    return concatenated, metadata


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the CLI tool."""

    parser = argparse.ArgumentParser(description="Create a random concatenation of audio clips.")
    parser.add_argument("src_path", type=Path, help="Path to the source audio file.")
    parser.add_argument(
        "durations",
        metavar="duration",
        type=str,
        nargs="+",
        help="Durations in seconds for each clip.",
    )
    parser.add_argument("--seed", type=int, default=None, help="Seed for random start positions.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("out.wav"),
        help="Output audio path (format inferred from extension).",
    )

    return parser.parse_args(argv)


def load_audio(path: Path) -> AudioSegment:
    """Load an audio file, raising an informative error on failure."""

    if not path.exists():
        raise AudioProcessingError(f"Source file does not exist: {path}")
    try:
        return AudioSegment.from_file(path)
    except Exception as exc:  # pragma: no cover - pydub raises many exception types
        raise AudioProcessingError(f"Failed to decode audio file '{path}': {exc}") from exc


def generate_random_cuts(
    src_path: Path | str,
    durations: Sequence[float | int | str],
    *,
    seed: int | None = None,
    output_path: Path | str | None = None,
) -> RandomCutsResult:
    """Generate a random concatenation of clips from ``src_path``.

    Args:
        src_path: Path to the source audio file.
        durations: Durations of each clip in seconds. Values are converted to
            floats, so integers and strings representing numbers are accepted.
        seed: Optional seed used to initialise the random number generator.
        output_path: Optional destination path to export the concatenated
            audio. When ``None`` the audio is not written to disk.

    Returns:
        ``RandomCutsResult`` containing the original audio segment, the
        concatenated output, and metadata for each generated clip.
    """

    try:
        duration_values = [float(value) for value in durations]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"All durations must be numeric values: {exc}") from exc

    rng = random.Random(seed)
    source = load_audio(Path(src_path))
    concatenated, metadata = build_random_clips_concatenation(source, duration_values, rng)

    result = RandomCutsResult(source=source, concatenated=concatenated, metadata=metadata)

    if output_path is not None:
        result.export(output_path)

    return result


def main(argv: Iterable[str] | None = None) -> None:
    """Entry point for the randcuts CLI."""

    args = parse_args(argv)

    result = generate_random_cuts(
        args.src_path,
        args.durations,
        seed=args.seed,
        output_path=args.out,
    )

    source = result.source
    src_ms = len(source)
    print(
        f"Loaded {args.src_path} ({src_ms} ms, {source.channels} ch, {source.frame_rate} Hz)"
    )

    for clip_meta in result.metadata:
        print(
            f"Clip {clip_meta.index}: dur={clip_meta.duration_ms} ms | start={clip_meta.start_ms} ms | fade={clip_meta.fade_ms} ms"
        )

    print(f"Exported concatenated audio to {args.out}")


if __name__ == "__main__":
    main()
