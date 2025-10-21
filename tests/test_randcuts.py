import random
from pathlib import Path

import pytest

pydub = pytest.importorskip("pydub")
AudioSegment = pydub.AudioSegment

import randcuts


def make_source(duration_ms: int, channels: int = 1, frame_rate: int = 44100) -> AudioSegment:
    """Create a silent AudioSegment with the requested properties."""

    return AudioSegment.silent(duration=duration_ms, frame_rate=frame_rate).set_channels(channels)


def test_convert_durations_to_ms_valid_rounding():
    durations = [0.5, 1.234, 0.001]
    assert randcuts._convert_durations_to_ms(durations) == [500, 1234, 1]


def test_convert_durations_to_ms_invalid_non_positive():
    with pytest.raises(ValueError):
        randcuts._convert_durations_to_ms([1.0, 0, -0.5])


def test_build_random_clips_concatenation_metadata_and_lengths():
    source = make_source(4000, channels=2)
    durations = [0.5, 1.0, 0.25]
    rng = random.Random(42)

    concatenated, metadata = randcuts.build_random_clips_concatenation(source, durations, rng)

    assert len(metadata) == len(durations)
    for index, clip_meta in enumerate(metadata):
        assert clip_meta.index == index
        assert clip_meta.duration_ms == randcuts._convert_durations_to_ms(durations)[index]
        assert 0 <= clip_meta.start_ms <= len(source) - clip_meta.duration_ms
        assert 0 <= clip_meta.fade_ms <= 300

    expected_length = sum(m.duration_ms for m in metadata)
    assert len(concatenated) == expected_length
    assert concatenated.channels == 2


def test_build_random_clips_concatenation_empty_durations_returns_silent_clip():
    source = make_source(1000, channels=1)
    rng = random.Random(0)

    concatenated, metadata = randcuts.build_random_clips_concatenation(source, [], rng)

    assert metadata == []
    assert len(concatenated) == 0
    assert concatenated.channels == source.channels


def test_build_random_clips_concatenation_rejects_duration_longer_than_source():
    source = make_source(1000)
    rng = random.Random(0)

    with pytest.raises(ValueError):
        randcuts.build_random_clips_concatenation(source, [2.0], rng)


def test_generate_random_cuts_returns_result(monkeypatch):
    source = make_source(3000)

    loaded_paths = []

    def fake_load_audio(path: Path) -> AudioSegment:
        loaded_paths.append(path)
        return source

    monkeypatch.setattr(randcuts, "load_audio", fake_load_audio)

    result = randcuts.generate_random_cuts("dummy.wav", [0.5, 0.25, 0.125], seed=123)

    assert loaded_paths == [Path("dummy.wav")]
    assert result.source is source
    assert len(result.metadata) == 3
    assert sum(meta.duration_ms for meta in result.metadata) == len(result.concatenated)


def test_generate_random_cuts_export_validates_suffix(monkeypatch, tmp_path):
    source = make_source(1500)
    monkeypatch.setattr(randcuts, "load_audio", lambda path: source)

    with pytest.raises(ValueError):
        randcuts.generate_random_cuts("dummy.wav", [0.5], output_path=tmp_path / "no_suffix")


def test_random_cuts_result_export_invokes_audio_export(monkeypatch, tmp_path):
    source = make_source(2000)
    monkeypatch.setattr(randcuts, "load_audio", lambda path: source)

    exported = {}

    def fake_export(self, path: Path, format: str):
        exported["path"] = path
        exported["format"] = format
        path.write_bytes(b"FAKE")

    monkeypatch.setattr(randcuts.AudioSegment, "export", fake_export)

    output_path = tmp_path / "clip.wav"
    result = randcuts.generate_random_cuts("dummy.wav", [0.5], output_path=output_path)

    assert exported["path"] == output_path
    assert exported["format"] == "wav"
    assert output_path.read_bytes() == b"FAKE"
    assert len(result.metadata) == 1
