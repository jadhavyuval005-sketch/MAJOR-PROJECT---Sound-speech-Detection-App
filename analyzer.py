"""Speech analysis.

Two analyzers are available, selected with the ANALYZER setting:

* ``quality``  (default) checks that a recording is usable (not silent, not too short,
  not clipped). It does NOT judge pronunciation, so ``auto_score`` stays None and the
  parent or clinician marks each word correct or incorrect after listening.
* ``wav2vec2`` runs a multilingual phoneme-recognition model, aligns the recognised
  phonemes with the expected ones, and produces a per-word score and error list.
  Needs torch + transformers and a model download. It has not been validated on
  Hindi-English child speech; treat its output as a screening aid only.
"""
import io
import re
import wave

import numpy as np

_STRIP = re.compile("[ːˑʰʱˈˌ̪̃ʲʷ]")


class AudioError(ValueError):
    pass


def read_wav(data: bytes):
    """16-bit PCM WAV bytes -> (mono float32 samples in [-1, 1], sample rate)."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(frames)
    except (wave.Error, EOFError) as exc:
        raise AudioError("Audio must be a valid WAV file") from exc
    if width != 2:
        raise AudioError("Audio must be 16-bit PCM WAV")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        x = x[: len(x) // channels * channels].reshape(-1, channels).mean(axis=1)
    return x, rate


def quality_check(x, rate, max_seconds):
    duration = len(x) / rate if rate else 0.0
    flags = []
    if duration < 0.3:
        flags.append("too_short")
    if duration > max_seconds:
        flags.append("too_long")
    if len(x) == 0:
        return duration, flags + ["silent"]
    if float(np.sqrt(np.mean(x**2))) < 0.003:
        flags.append("silent")
    if float(np.mean(np.abs(x) >= 0.99)) > 0.01:
        flags.append("clipped")
    hop = max(int(rate * 0.025), 1)
    n = len(x) // hop
    if n:
        frame_rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1))
        if "silent" not in flags and float(np.mean(frame_rms > 0.01)) < 0.08:
            flags.append("mostly_silence")
    return duration, flags


def normalize(tokens):
    out = []
    for t in tokens:
        t = _STRIP.sub("", t)
        if t:
            out.append(t)
    return out


def align(expected, got):
    """Levenshtein alignment. Returns (edit_distance, errors)."""
    n, m = len(expected), len(got)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if expected[i - 1] == got[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    errors, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (expected[i - 1] != got[j - 1]):
            if expected[i - 1] != got[j - 1]:
                errors.append({"type": "substitution", "position": i - 1,
                               "expected": expected[i - 1], "got": got[j - 1]})
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            errors.append({"type": "omission", "position": i - 1, "expected": expected[i - 1], "got": None})
            i -= 1
        else:
            errors.append({"type": "addition", "position": i, "expected": None, "got": got[j - 1]})
            j -= 1
    errors.reverse()
    return d[n][m], errors


def score_phonemes(expected, got):
    exp, rec = normalize(expected), normalize(got)
    dist, errors = align(exp, rec)
    score = max(0.0, 1.0 - dist / max(len(exp), len(rec), 1))
    return round(score, 3), errors


class Wav2Vec2Recognizer:
    """Lazy-loaded phoneme recogniser. Imports torch/transformers only when used."""

    _cache = {}

    def __init__(self, model_name):
        if model_name not in self._cache:
            import torch
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

            self._cache[model_name] = (
                Wav2Vec2Processor.from_pretrained(model_name),
                Wav2Vec2ForCTC.from_pretrained(model_name).eval(),
                torch,
            )
        self.processor, self.model, self.torch = self._cache[model_name]

    def recognize(self, x, rate):
        if rate != 16000:
            t = np.arange(int(len(x) * 16000 / rate)) * rate / 16000
            x = np.interp(t, np.arange(len(x)), x).astype(np.float32)
        inputs = self.processor(x, sampling_rate=16000, return_tensors="pt")
        with self.torch.no_grad():
            logits = self.model(inputs.input_values).logits
        text = self.processor.batch_decode(self.torch.argmax(logits, dim=-1))[0].strip()
        return text.split() if " " in text else list(text)


def analyze(data: bytes, word: dict, analyzer: str, max_seconds: int, model_name: str = ""):
    x, rate = read_wav(data)
    duration, flags = quality_check(x, rate, max_seconds)
    result = {"duration_s": round(duration, 2), "quality_flags": flags,
              "auto_score": None, "recognized": None, "errors": []}
    unusable = {"silent", "too_short", "too_long", "mostly_silence"} & set(flags)
    if analyzer == "wav2vec2" and not unusable:
        tokens = Wav2Vec2Recognizer(model_name).recognize(x, rate)
        score, errors = score_phonemes(word["ipa"], tokens)
        result.update(auto_score=score, recognized=" ".join(tokens), errors=errors)
    return result
