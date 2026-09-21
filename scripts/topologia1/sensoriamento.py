#!/usr/bin/env python3
"""
Pipeline de sensoriamento COMPARTILHADO pelas 3 ramificacoes (MQTT/HTTP/CoAP).

O que nao muda entre protocolos de aplicacao:
  1. capturar_amostra_de_audio(): sorteia ~10 s continuos de audio real do
     dataset na RAM (tmpfs /mnt/dataset-ram) com a distribuicao alvo por classe
     (ambiente 50%, femea 30%, macho 10%, outros 10%) e "le" em tempo real
     (1s de leitura por segundo de audio), simulando um microfone;
  2. inferir_classificacao(): roda o modelo Residual (mel + tflite) na borda
     sobre a ultima janela dos 10 s ouvidos;
  3. descritores(): frequencia dominante + RMS da janela.

O metadado gerado carrega 'classe_real' (a classe do audio ouvido) e 'correto'
(predicao == classe real), permitindo validar depois a taxa de deteccao de cada
classe e a acuracia dos sensores.

O que muda (e fica fora daqui): apenas o TRANSPORTE do metadado ate o servidor.
"""

import json
import os
import time

import numpy as np

SR = 8000
WINDOW = 9984
DATASET_RAM = '/mnt/dataset-ram'

# Distribuicao alvo por classe no sorteio dos sensores (50/30/10/10):
#   0 = aedes macho, 1 = aedes femea, 2 = outros mosquitos, 3 = ruido ambiental.
PESOS_CLASSES = {0: 0.10, 1: 0.30, 2: 0.10, 3: 0.50}

# Tempo de "escuta" de cada ciclo de sensoriamento (s).
ESCUTA_S = 10.0
# Numero de janelas de 9984 amostras (1,248 s) por ciclo (~9,98 s de audio).
JANELAS_POR_ESCUTA = int(round(ESCUTA_S * SR / WINDOW))

_CACHE = None


def carregar_dataset(dataset_dir=DATASET_RAM):
    """Mapeia os .bin por classe (memmap compartilhado da tmpfs)."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    with open(os.path.join(dataset_dir, 'meta.json')) as f:
        meta = json.load(f)['classes']
    _CACHE = {
        int(classe): np.memmap(
            os.path.join(dataset_dir, '%s.bin' % classe),
            dtype=np.float32, mode='r',
            shape=(meta[classe]['count'], WINDOW))
        for classe in meta if int(meta[classe]['count']) > 0
    }
    return _CACHE


def ler_em_tempo_real(janela, chunk_seg=0.1):
    """Le o sinal em tempo real: 1s de leitura por segundo de audio."""
    chunk = max(1, int(round(SR * chunk_seg)))
    for i in range(0, len(janela), chunk):
        _ = janela[i:i + chunk]
        time.sleep(chunk / SR)


def capturar_amostra_de_audio(rng, dataset_dir=DATASET_RAM, tempo_real=True,
                              janelas=JANELAS_POR_ESCUTA):
    """Captura ~10 s continuos de audio real de uma classe sorteada.

    A classe e sorteada com os pesos PESOS_CLASSES (ambiente 50%, femea 30%,
    macho 10%, outros 10%) e as janelas sao retiradas em sequencia do mesmo
    bloco da classe (janelas consecutivas = audio continuo). Se `tempo_real`,
    a leitura simula o microfone: ~1 s de espera por segundo de audio.

    Retorna (classe_real, janela_inicial, indice_classificada, janela_ouvida):
      - classe_real:     classe real do audio ouvido;
      - janela_inicial:  indice do inicio do trecho de 10 s no .bin da classe;
      - indice_class:    indice da janela classificada (a ultima dos 10 s);
      - janela_ouvida:   sinal 9984 (float32) que alimenta o modelo.
    """
    dataset = carregar_dataset(dataset_dir)
    classes = sorted(dataset)
    pesos = [PESOS_CLASSES.get(c, 0.0) for c in classes]
    total = sum(pesos)
    pesos = [p / total for p in pesos] if total > 0 else None
    classe_real = int(rng.choice(classes, p=pesos))

    bloco = dataset[classe_real]
    n = len(bloco)
    k = min(janelas, n)
    inicio = int(rng.integers(n - k + 1)) if n >= k else 0
    janela_ouvida = np.asarray(bloco[inicio + k - 1])
    if tempo_real:
        ler_em_tempo_real(np.asarray(bloco[inicio:inicio + k]).reshape(-1))
    return classe_real, inicio, inicio + k - 1, janela_ouvida


def inferir_classificacao(janela, classificador):
    """Roda o modelo na borda: retorna (probs, classe_nome)."""
    return classificador.classificar(janela)


def descritores(samples):
    n = len(samples)
    rms = float(np.sqrt(np.mean(np.square(samples))))
    spec = np.abs(np.fft.rfft(samples))
    freq = float(np.fft.rfftfreq(n, 1.0 / SR)[int(np.argmax(spec))])
    return round(freq, 1), round(rms, 4)


def montar_metadado(classe_real, indice, probs, classe, freq, rms, seq,
                    sensor, cluster, janela_inicial=None, tempo_agora=None):
    """Metadado da classificacao (mesmo schema nas 3 ramificacoes).

    'correto' e True quando a classe de maior confianca coincide com a classe
    real do audio ouvido (verificacao local de baixo custo, usada depois para
    medir taxa de deteccao por classe e acuracia dos sensores).
    """
    agora = tempo_agora if tempo_agora is not None else time.time()
    return {
        'ts': round(agora, 3),
        'sensor': sensor,
        'cluster': cluster,
        'classe_real': int(classe_real),
        'janela': indice,
        'janela_inicial': janela_inicial,
        'classe': classe,
        'correto': bool(int(np.argmax(probs)) == int(classe_real)),
        'presente': classe != 'ambiente',
        'conf': round(float(max(probs)), 3),
        'probs': [round(float(p), 3) for p in probs],
        'freq': freq,
        'rms': rms,
        'seq': seq,
    }