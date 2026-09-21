#!/usr/bin/env python3
"""
Classificador do modelo Residual de mosquitos na borda.

Carrega model_float16.tflite (entrada/saída float32, quantizado float16) via
tflite-runtime e expõe classificar(sinal): mel (NumPy) -> predict -> argmax.

Uso:
  c = Classificador()
  probs, classe = c.classificar(signal_9984)
"""

import os

import numpy as np
from tflite_runtime.interpreter import Interpreter  # noqa: F401

import mel

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, 'model_float16.tflite')

CLASS_NAMES = {
    0: 'aedes_aegypti_macho',
    1: 'aedes_aegypti_femea',
    2: 'outros_mosquitos',
    3: 'ambiente',
}


class Classificador:
    def __init__(self, model_path=None, verbose=True):
        self.path = model_path or MODEL_PATH
        self._interp = Interpreter(model_path=self.path)
        self._interp.allocate_tensors()
        self._in = self._interp.get_input_details()[0]
        self._out = self._interp.get_output_details()[0]
        if verbose:
            print('[classificador] modelo carregado: %s' % self.path, flush=True)

    def classificar(self, signal):
        x = mel.feature(signal)
        dt = self._in['dtype']
        if dt != np.dtype('float32'):
            scale, zero = self._in.get('quantization', (1.0, 0))
            unified = (x / scale) + zero
            x = np.clip(unified, dt.min(), dt.max()).astype(dt)
        self._interp.set_tensor(self._in['index'], x)
        self._interp.invoke()
        out = self._interp.get_tensor(self._out['index'])
        probs = np.asarray(out, dtype=float).reshape(-1)
        k = int(np.argmax(probs))
        return probs, CLASS_NAMES.get(k, 'classe_%d' % k)