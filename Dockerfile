FROM mn-wifi:v1

# Camada do experimento WSN-WiFi (topologia1: MQTT/HTTP/CoAP). A base
# mn-wifi:v1 ja fornece containernet + mininet-wifi, hostapd, iw, Open vSwitch
# e numpy. Aqui garantimos apenas o runtime de fato usado pelo experimento
# (removido o que nao e usado: MQTT-SN/bisquitt/gateway e welcome.sh).

# Broker MQTT do experimento (mosquitto) + clientes de linha de comando
RUN apt-get update && apt-get install -y --no-install-recommends \
        mosquitto mosquitto-clients && \
    rm -rf /var/lib/apt/lists/*

# Dependencias Python do experimento:
#   - docker, pyyaml, six  : biblioteca do containernet
#   - paho-mqtt, aiocoap   : transportes MQTT e CoAP
#   - tflite-runtime, numpy: inferencia do modelo nos sensores
#   - librosa, matplotlib  : preparacao do dataset e graficos de analise
RUN pip3 install --no-cache-dir \
        docker pyyaml six \
        paho-mqtt aiocoap \
        tflite-runtime numpy \
        librosa matplotlib

# PYTHONPATH do Containernet/mininet-wifi
ENV PYTHONPATH=/opt/containernet:$PYTHONPATH

# Diretorios de persistencia (bind dos volumes do host em up.sh)
RUN mkdir -p /app/scripts /app/config /app/dados
WORKDIR /app

# Sem entrypoint: up.sh inicia o openvswitch e deixa o bash do container ativo
CMD ["/bin/bash"]