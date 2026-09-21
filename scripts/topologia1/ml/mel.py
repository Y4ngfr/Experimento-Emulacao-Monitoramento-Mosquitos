#!/usr/bin/env python3
"""
Pré-processamento do modelo Residual (classificação de mosquitos) em NumPy puro.

Espelha fielmente o pipeline de treino
(Engine/Models/Process/Residual_Process.py do Audio-Classification_Library):

  áudio 8kHz -> janela 9984 amostras (1,248s) ->
  melspectrogram(n_mels=512, n_fft=1024, hop_length=256) ->
  power_to_db(ref=max, top_db=80)/80 + 1 ->
  reshape (512,40,1) -> +1 linha de zeros -> (1,513,40,1) float32

Os sensores importam APENAS NumPy aqui (sem librosa). O filterbank mel
(Slaney) é reconstruído em `mel_filterbank` para bater com
librosa.filters.mel(sr=8000, n_fft=1024, n_mels=512, fmax=4000).
"""

import numpy as np

SR = 8000
N_FFT = 1024
HOP = 256
N_MELS = 512
N_BINS = N_FFT // 2 + 1          # 513
WINDOW_SAMPLES = 9984            # hop*(fatores-1) = 256*39 -> 1,248s em 8kHz
N_FRAMES = WINDOW_SAMPLES // HOP + 1  # 40 (com o padding central de center=True)
AMIN = 1e-10
TOP_DB = 80.0
DB_FACTOR = 80.0


def hann_periodic(n):
    """Hann periódico equivalente a scipy.signal.get_window('hann', n, fftbins=True)."""
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / n)


def mel_to_hz(mels):
    """Escala mel Slaney invertida (librosa.mel_to_hz)."""
    mels = np.asanyarray(mels)
    f_min = 0.0
    f_sp = 200.0 / 3.0
    min_log_hz = 1000.0
    min_log_mel = (min_log_hz - f_min) / f_sp   # 15.0 (junção linear/log contínua)
    logstep = np.log(6.4) / 27.0
    linear = f_min + f_sp * mels
    logmel = min_log_hz * np.exp(logstep * (mels - min_log_mel))
    return np.where(mels >= min_log_mel, logmel, linear)


def hz_to_mel(freqs):
    """Escala mel Slaney (librosa.hz_to_mel)."""
    freqs = np.asanyarray(freqs)
    f_min = 0.0
    f_sp = 200.0 / 3.0
    min_log_hz = 1000.0
    min_log_mel = (min_log_hz - f_min) / f_sp   # 15.0
    logstep = np.log(6.4) / 27.0
    lin = (freqs - f_min) / f_sp
    with np.errstate(divide='ignore', invalid='ignore'):
        logmel = min_log_mel + np.log(freqs / min_log_hz) / logstep
    return np.where(freqs < min_log_hz, lin, logmel)


def mel_filterbank(sr=SR, n_fft=N_FFT, n_mels=N_MELS, fmax=None):
    """Filterbank mel (512 x 513) equivalente a librosa.filters.mel(norm='slaney')."""
    if fmax is None:
        fmax = float(sr) / 2.0
    fft_freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)                 # 0..sr/2
    mel_bins = mel_to_hz(np.linspace(hz_to_mel(0.0),
                                     hz_to_mel(fmax), n_mels + 2))
    fb = np.empty((n_mels, N_BINS), dtype=np.float64)
    for i in range(n_mels):
        left, center, right = mel_bins[i], mel_bins[i + 1], mel_bins[i + 2]
        lower = (fft_freqs - left) / (center - left)
        upper = (right - fft_freqs) / (right - center)
        fb[i] = np.maximum(0.0, np.minimum(lower, upper))
    # Norma 'slaney': 2 / (right - left) por linha
    enorm = 2.0 / (mel_bins[2:n_mels + 2] - mel_bins[:n_mels])
    fb *= enorm[:, np.newaxis]
    return fb


FB = mel_filterbank()  # (512, 513), float64


def _power_to_db(power):
    """10*log10(power/ref) com ref=max e clip top_db (librosa.power_to_db)."""
    ref = float(power.max())
    log_spec = 10.0 * np.log10(np.maximum(AMIN, power)) - 10.0 * np.log10(np.maximum(AMIN, ref))
    return np.maximum(log_spec, log_spec.max() - TOP_DB)


def _stft_power(signal):
    """STFT (hann 1024, hop 256, center=True/pad constante) e espectro de potência.

    Retorna (N_FRAMES=40, N_BINS=513).
    """
    signal = np.asarray(signal, dtype=np.float64).reshape(-1)
    if len(signal) < WINDOW_SAMPLES:
        raise ValueError('sinal curto: %d < %d amostras' % (len(signal), WINDOW_SAMPLES))
    signal = signal[:WINDOW_SAMPLES]
    pad = N_FFT // 2
    y = np.pad(signal, (pad, pad), mode='constant')
    win = hann_periodic(N_FFT)
    starts = HOP * np.arange(N_FRAMES)
    frames = np.empty((N_FRAMES, N_FFT), dtype=np.float64)
    for i, s in enumerate(starts):
        frames[i] = y[s:s + N_FFT]
    spec = np.fft.rfft(frames * win, axis=1)
    return np.abs(spec) ** 2.0  # (40, 513)


def feature(signal):
    """Converte um bloco de áudio (>=9984 amostras, 8kHz) para (1,513,40,1) float32."""
    power = _stft_power(signal)              # (40, 513)
    mel = FB @ power.T                       # (512, 40)
    db = (_power_to_db(mel) / DB_FACTOR) + 1.0
    out = np.zeros((1, N_MELS + 1, N_FRAMES, 1), dtype=np.float32)
    out[0, :N_MELS, :, 0] = db.astype(np.float32)
    return out