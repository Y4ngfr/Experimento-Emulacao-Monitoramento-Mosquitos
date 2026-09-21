### Fundamentação

#### Padrão Wi-Fi (802.11) e IEEE 802.15.4
O Wi-Fi é uma família de dezenas de especificações do padrão IEEE 802.11. Alguns notáveis são: IEEE 802.11be (Wi-Fi 7), IEEE 802.11ax (Wi-Fi 6/ Wi-Fi 6E), IEEE 802 802.11n (Wi-Fi 4) e IEEE 802.11ac (Wi-Fi 5). Os mais comuns em ambientes domésticos são o Wi-Fi 5 e Wi-Fi 6.
A abrangência de padrões Wi-Fi é um aspecto que diferencia o padrão IEEE 802.15.4, que é um padrão único e estável que serve como base técnica de redes de baixa taxa, baixo consumo de energia e curto alcance, conhecidas como LR-WPANs (Low-Rate Wireless Personal Area Networks).

#### Canais
Canais são faixas de frequências de operação que as tecnologias de comunicação sem fio oferecem. Elas existem por diversos motivos, como por exemplo, evitar congestionamento, aumentar a segurança de comunicação, gerenciar interferências, balancear velocidade e alcance, entre outros. O padrão Wi-Fi possui 14 canais (variando conforme o país), mas cada canal tem largura de 20 MHz e espaçamento de 5 MHz (se sobrepõem). A maioria das redes residenciais brasileiras operam em 11 canais na banda de 2.4 GHz e 9 canais na banda de 5 GHz.

#### Interfaces de Rede
...

#### Deamon
Um deamon é um termo de sistemas Unix/Linux para um processo que roda em segundo plano sem interface com o usuário, geralmente esperando por eventos ou prestando um serviço contínuo. Ele roda desacoplado do terminal, geralmente inicia junto com o sistema, fica em loop esperando requisições/eventos e geralmente tem nome terminado em d por convenção: sshd, httpd, crond, systemd, wmediumd, etc.

Alguns exemplos de deamons:

| Daemon | O que faz |
|-----------|-----------|
|sshd|Aceita conexões SSH|
|crond|Executa tarefas agendadas|
|hostapd|Transforma uma interface WiFi em Access Point|
|mosquitto|Broker MQTT (fica escutando na porta 1883)|
|wmediumd|Simula interferência wireless|
|systemd|Gerencia todos os outros daemons|

#### Network Namespace (netns)
Namespace de rede

#### Ponte L2 (bridge da camada 2)
A camada L2 é a camada de Enlace do modelo OSI. Uma ponte L2 é um dispositivo que encaminha quadros por endereço MAC, sem olhar para o IP. É o que um switch faz.

#### Forwarding L3 (roteamento)
A camada L3 é a camada de Rede do modelo OSI. Portanto o forwarding L3 é o roteamento de pacotes pelo IP de uma interface para outra. É o que um roteador faz.

A tabela abaixo mostra algumas diferenças entre a ponte L2 e o forwarding L3:

| Ponte L2             | Roteador L3 |                     |
| -------------------- | ----------- | ------------------- |
| Olha                 | MAC         | IP                  |
| Modifica pacote?     | Não         | Sim (TTL, checksum) |
| Domínio de broadcast | Mesmo       | Separado            |
| Exemplo              | Switch      | Roteador            |
A tabela abaixo relembra algumas camadas do modelo OSI 

| Camada | Nome       | Endereço | Exemplo        |
| ------ | ---------- | -------- | -------------- |
| L1     | Física     | —        | Cabo, rádio    |
| L2     | Enlace     | MAC      | Ethernet, WiFi |
| L3     | Rede       | IP       | IPv4/IPv6      |
| L4     | Transporte | Porta    | TCP/UDP        |

#### OVS bridge (Open vSwitch bridge)

O Open vSwitch é um switch virtual de código aberto, usado em virtualização e no Mininet. Ele implementa:

- Bridging L2.
- VLANs.
- OpenFlow (protocolo de controle programável de switches).
- Túneis (VXLAN, GRE).
- QoS, mirroring, etc.

-----------------------------------------------------------------------

### Comandos Básicos de Controle

```Bash fold title:Exibe_a_versão_do_Mininet red:1-4
sudo mn --version       # Exibe a versão
```



```Bash fold title:Exibe_o_Menu_Ajuda red:1-4
sudo mn --help          # Exibe o menu de ajuda
```



```Bash fold title:Limpa_execuções_mal_feitas red:1-4
sudo mn -c              # Limpa execuções mal feitas
```



```Bash fold title:Inicia_o_Mininet_WiFi red:1-4
sudo mn --wifi          # Inicia o Mininet WiFi
```
Além de abrir a interface CLI do Mininet, esse comando irá criar uma topologia que consiste em duas estações conectadas a um ponto de acesso através de um meio sem fio. Também há um controlador SDN conectado ao ponto de acesso.

```Bash fold title:Parâmetros_para_iniciar_o_Mininet_WiFi red:1-4
mininet-wifi> sudo mn --wifi --ssid=new-ssid --channel=1
```
É possível definir o ssid da rede e o canal.

-----------------------------------------------------------------------

### Comandos da Interface CLI do Mininet WiFi

```Bash fold title:Mininet-WiFi_CLI red:1-4
mininet-wifi> nodes
```
Lista os nós que fazem parte da topologia.

```Bash fold title:Mininet-WiFi_CLI red:1-4
mininet-wifi> sta1 iw dev sta1-wlan0 info
```
É possível rodar comandos linux nos nós emulados do Mininet. Neste exemplo rodamos um comando do utilitário iw. Este comando lista as informações da interface de Wi-Fi sta1-wlan0 como qual SSID está associado, frequência, canal, entre outros.

```Bash fold title:Mininet-WiFi_CLI red:1-4
mininet-wifi> xterm sta1
```
Abre terminal do nó sta1

```Bash fold title:Mininet-WiFi_CLI red:1-4
mininet-wifi> pingall
```
Testa a conectividade através de ping de todos contra todos

```Bash fold title:Mininet-WiFi_CLI red:1-4
mininet-wifi> py sta1.position
```
Retorna posição de sta1

```Bash fold title:Mininet-WiFi_CLI red:1-4
mininet-wifi> py sta1.setPosition('10,0,0')
```
Define a posição de sta1

-----------------------------------------------------------------------

### Arquitetura de Classes do Mininet-WiFi

#### Camada de Topologia
Essa camada é representada principalmente pela classe Mininet_wifi, sendo a classe principal do Mininet-WiFi, análoga à Mininet original, definida em mn_wifi/net.py . 
Ela orquestra todo ciclo de vida da rede.

Responsabilidades principais: 
+ criar e armazenar nós (addStation, addAcessPoint, addHost, addCar, addController)
+ criar links (addLink)
+ configurar o ambiente sem fio (configureNodes)
+ aplicar modelos de propagação (setPropagationModel)
+ aplicar modelos de mobilidade (setMobilityModel)
+ plotar topologia (plotGraph)
+ controlar o ciclo (build(), start(), stop())

Atributos relevantes:
+ Listas internas:
	stations, aps, cars, hosts, switches, controllers
+ parâmetros globais:
	wmediumd_mode, ifb, noise_th, fading_cof

A classe Mininet_wifi é quem instancia os objetos das classes de nós (Station, AcessPoint) e de enlace (WirelessLink, wmediumd).

#### Camada de Nós

#### Camada de Enlace
Define diversas classes importantes em mn_wifi/link.py:
IntfWireless: análoga a Intf do Mininet, representa a interface de rádio de um nó, com atributos como mac, ip, range, channel, freq, txpower.
WirelessLink: enlace lógico dentre uma estação e um AP (ou entre APs)
wmediumd: liga o enlace ao daemon wmediumd
mesh: 802.11s
adhoc: IBSS
physicalMesh
wifiDirect


#### Meio sem Fio
No meio sem fio existem duas possibilidades: mn_wifi/wmediumdConnector.py e Traffic Control (tc),
O wmediumd é um deamon externo que atua decidindo se um pacote pode ou não trafegar entre duas interfaces, com base em distância/nível de sinal

#### Mobilidade

#### Propagação de Sinal
Definido em mn_wifi/propagationModels.py. A classe PropagationModel implementa fórmulas como Friis, Log-Distance, etc.
É usado por IntfWireless e WirelessLink para popular valores de RSSI exibidos no CLI iw dev ... link


#### Carregamento de Driver

mac80211_hwsim é um módulo do kernel Linux que cria interfaces WiFi virtuais em software

#### Carregamento de Dispositivos Físicos

#### Interface de Controle

wintf: atributo da classe que armazena um dicionário em Python com as interfaces de rede sem fio de um nó (seja de uma estação ou ponto de acesso).

O Mininet suporta dois tipos de pontos de acesso: OVSAP/OVSKernelAP e UserAP.
OVSAP/OVSKernelAP: é executado no kernel.
UserAP: é executado no espaço de usuário.

Eles possuem essa diferenciação pois foram implementados por cima de switches do Mininet, que historicamente possuem essa característica. A diferença de implementação deles faz com que o OVSAP tenha um desempenho muito melhor do que o UserAP, porém o UserAP é muito mais flexível para pesquisas e desenvolvimento, sendo mais fácil de trabalhar com ele. Vale mencionar que o projeto BOFUSS trabalhou para mitigar muitos problemas de performance do UserAP, porém é necessário instalar o BOFUSS manualmente no ambiente do Mininet-WiFi.

wmedium:

-----------------------------------------------------------------------

### Utilitários de rede do Linux

#### Iw/Iwconfig
Essa é uma interface de linha de comando que faz comunicação direta com a driver da placa Wi-Fi nos sistemas Linux. Todas as interfaces gráficas Linux rodam esse utilitário por baixo dos panos para configuração da conexão Wi-Fi no sistema.
O iw é a versão mais atualizada do utilitário, feito para substituir o iwconfig.
Esse utilitário permite configurar e exibir informações sobre interfaces de rede Wi-Fi. Dentre outras coisas é possível:
+ Ver em qual canal sua placa está operando
+ Ver a intensidade do sinal
+ Ver a taxa de transmissão
+ Ver qual frequência está sendo usada
+ Ver o endereço MAC do roteador
+ Forçar a placa a usar uma banda específica
+ Escanear as redes Wi-Fi ao redor

*Utilização e comandos básicos*:

```Bash fold title:utilitario_iw/iwconfig red:1-4
iw dev
```
Vê o nome da interface de rede. Geralmente wlan0 ou wlp1s0. 

```Bash fold title:utilitario_iw/iwconfig red:1-4
iw dev wlan0 info
```
Vê as informações técnicas da conexão atual (canal, frequência, sinal, velocidade, etc).

```Bash fold title:utilitario_iw/iwconfig red:1-4
iw dev wlan0 scan
```
Lista as redes identificadas. A saída desse comando é densa e possui muitas informações de cada rede.

```Bash fold title:utilitario_iw/iwconfig red:1-4
iw dev wlan0 scan | grep -E "SSID:|signal:|DS Parameter set|primary channel"
```
Uma opção com uma formatação mais limpa de saída é filtrar as informações para mostrar apenas o SSID (nome da rede), potência do sinal e canal.

```Bash fold title:utilitario_iw/iwconfig red:1-4
iw dev wlan0 set freq 5GHz
```
Força a conexão a usar apenas a banda de 5GHz.

```Bash fold title:utilitario_iw/iwconfig red:1-4
iw dev wlan0 link
```
Utilizando o parâmetro link ao invés de info é possível obter o nível de sinal percebido pelo nó, o bitrate e pacotes transmitidos e recebidos.

#### Ping
É o utilitário mais mais famoso e antigo da história das redes de computadores. Hoje em dia está presente em todos os sistemas operacionais e até mesmo em roteadores. Ele serve principalmente para testar a conexão entre dispositivos da rede.
O ping utiliza o protocolo ICMP (Internet Control Message Protocol), que é um protocolo da camada de rede usado exclusivamente para enviar mensagens de erro e informações operacionais entre roteadores e hosts, não sendo usado para transportar dados de usuário. O ICMP também é empregado em outros usos além do ping, como por exemplo: anúncio de erro pelo roteador, controle de congestionamento, redirecionamento de rota, traceroute, entre outros.

É possível utilizar o ping para a internet externa. O utilitário faz o trabalho de buscar a tradução (DNS) automaticamente. Abaixo segue um exemplo de saída de um comando ping.

```Bash fold title:utilitario_ping red:1-4
ping google.com
PING google.com (142.250.217.78) 56(84) bytes of data.
64 bytes from 142.250.217.78: icmp_sq=1 ttl=115 time=8.32 ms
64 bytes from 142.250.217.78: icmp_seq=2 ttl=115 time=7.45 ms
64 bytes from 142.250.217.78: icmp_seq=3 ttl=115 time=9.01 ms
```

+ icmp_seq: número sequencial do pacote. Se pular números significa que o pacote foi perdido no caminho.
+ ttl: número máximo de saltos (roteadores) que um pacote pode atravessar. Começa em 64 ou 128 e vai diminuindo, se chegar em 0 o pacote é descartado para não ficar vagando indefinidamente na internet. Essa métrica é comumente chamada de TTL. 
+ time: tempo de ida e volta (round trip time - RTT). 

Alguns parâmetros são uteis:

+ -i define quanto tempo entre cada pacote.
+ -c define uma quantidade de pacotes icmp que serão enviados (caso contrário ele fica mandando indefinidamente).
+ -s define o tamanho do pacote.
+ -4 força o uso de IPv4.
+ -t altera o TTL.

#### Ip
É um utilitário que serve para configurar, visualizar e gerenciar todos os elementos de rede do kernel linux, como:
+ Interfaces de Rede (eth0, wlan0, etc)
+ Endereços IP (IPv4 e IPv6)
+ Tabelas de Roteamento (para onde os pacotes devem ir)
+ ARP (vizinhança)
+ Túneis, bridges, VLANs e muito mais

A estrutura do comando ip é simples:

```Bash fold title:utilitario_ip red:1-4
ip [opções] objeto comando [argumentos]
```

+ Objeto: o que você quer mexer (link, addr, route, neigh).
	+ link: gerencia interfaces de rede (ligar/desligar, MAC, MTU)
	+ addr: gerencia os endereços ips das interfaces
	+ route: gerencia a tabela de roteamento
	+ neigh: gerencia a tabela ARP (mapeia IP para MAC)
	
+ Comando: o que fazer com ele (show, add, del, set).

Alguns comando básicos mais utilizados:

```Bash fold title:utilitario_ip red:1-4
ip addr show
```
Vê todas as interfaces de rede e seus IPs.

```Bash fold title:utilitario_ip red:1-4
ip addr show wlan0
```
Vê apenas informações sobre a interface WiFi.

```Bash fold title:utilitario_ip red:1-4
ip route show
```
Vê a tabela de roteamento (para onde os pacotes vão).

```Bash fold title:utilitario_ip red:1-4
ip link set wlan0 down   # Desliga o Wi-Fi
ip link set wlan0 up     # Liga o Wi-Fi novamente
```


```Bash fold title:utilitario_ip red:1-4
sudo ip addr add 192.168.1.100/24 dev wlan0   # Adiciona um IP fixo
sudo ip addr del 192.168.1.100/24 dev wlan0   # Remove esse IP
```
Adiciona um ip novo na interface wlan0 (é possível ter mais de um ip na mesma interface, para por exemplo se comunicar em redes diferentes).