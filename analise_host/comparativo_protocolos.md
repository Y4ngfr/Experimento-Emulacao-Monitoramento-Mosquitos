
# Comparativo por protocolo e carga (media±desvio das runs)

> Graficos de barras agrupadas (3 protocolos x carga, media±desvio das runs)
> em \`analise_host/graficos_comparativo/\` (um PNG por metrica):
> \`broker_rx_kbps\`, \`app_lat_media_global_ms\`, \`app_lat_p99_ms_all\`,
> \`app_goodput_sustentado_kbps\`, \`app_gaps\`.
> Nota: a latencia media usa o valor **global real** (recomputado dos
> cient\*.log), nao a media de janelas do CSV.



## Aplicacao

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- |
| app_lat_p50_ms | 10 | 1.31±0.015(n=3) | 4.29±0.197(n=3) | 6.71±0.167(n=3) |
| app_lat_p50_ms | 20 | 1.38±0.0185(n=3) | 4.81±0.172(n=3) | 7.47±0.78(n=3) |
| app_lat_p50_ms | 30 | 1.44±0.0346(n=3) | 3.89±0.176(n=3) | 6.51±0.109(n=3) |
| app_lat_p50_ms | 40 | 1.4±0.023(n=3) | 3.91±0.0465(n=3) | 6.33±0.442(n=3) |
| app_lat_p50_ms | 50 | 1.52±0.0191(n=3) | 3.82±0.0445(n=3) | 6.13±0.572(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| app_lat_p90_ms | 10 | 2.09±0.0963(n=3) | 8.38±1.47(n=3) | 12.9±1.28(n=3) |
| app_lat_p90_ms | 20 | 2.6±0.403(n=3) | 9.42±0.904(n=3) | 16.7±4.12(n=3) |
| app_lat_p90_ms | 30 | 3.94±0.888(n=3) | 8.1±0.742(n=3) | 14.5±2.13(n=3) |
| app_lat_p90_ms | 40 | 5.84±2.46(n=3) | 20.6±13.8(n=3) | 16.3±3.47(n=3) |
| app_lat_p90_ms | 50 | 111.7±91.2(n=3) | 1028.1±6.09(n=3) | 21.4±5.35(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| app_lat_p99_ms | 10 | 3.43±0.82(n=3) | 13.4±2.8(n=3) | 18±3.33(n=3) |
| app_lat_p99_ms | 20 | 4.31±0.727(n=3) | 14±1.14(n=3) | 23.6±1.2(n=3) |
| app_lat_p99_ms | 30 | 111.5±57.8(n=3) | 1197.2±158.0(n=3) | 645.3±70.6(n=3) |
| app_lat_p99_ms | 40 | 260.3±80.4(n=3) | 1505.6±431.4(n=3) | 1048.1±125.6(n=3) |
| app_lat_p99_ms | 50 | 463.1±40.6(n=3) | 2200.9±196.2(n=3) | 1882.6±308.6(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| app_lat_p99_ms_all | 10 | 4.37±1.32(n=3) | 39.4±4.82(n=3) | 39.3±20.7(n=3) |
| app_lat_p99_ms_all | 20 | 7.42±2.45(n=3) | 38.6±5.27(n=3) | 54.6±12.2(n=3) |
| app_lat_p99_ms_all | 30 | 214.3±6.49(n=3) | 1739.7±533.5(n=3) | 1907.9±722.4(n=3) |
| app_lat_p99_ms_all | 40 | 483.4±111.4(n=3) | 3816.4±2525.8(n=3) | 2693.6±114.6(n=3) |
| app_lat_p99_ms_all | 50 | 708.6±108.7(n=3) | 4350.9±1.14(n=3) | 2923.6±22.7(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| app_goodput_media_kbps | 10 | 1.62±0.000169(n=3) | 1.54±0.0328(n=3) | 1.62±0.000809(n=3) |
| app_goodput_media_kbps | 20 | 3.25±0.00282(n=3) | 3.08±0.0305(n=3) | 3.24±0.00116(n=3) |
| app_goodput_media_kbps | 30 | 16.5±2.17(n=3) | 6.68±0.382(n=3) | 7.44±0.192(n=3) |
| app_goodput_media_kbps | 40 | 15.7±8.32(n=3) | 9.89±0.467(n=3) | 8.11±1.74(n=3) |
| app_goodput_media_kbps | 50 | 33.4±1.83(n=3) | 9.09±0.583(n=3) | 9.69±1.11(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| app_goodput_sustentado_kbps | 10 | 1.68±5.77e-05(n=3) | 1.62±0.0216(n=3) | 1.68±0.000896(n=3) |
| app_goodput_sustentado_kbps | 20 | 3.35±0.00128(n=3) | 3.17±0.0403(n=3) | 3.35±0.000872(n=3) |
| app_goodput_sustentado_kbps | 30 | 4.96±0.106(n=3) | 4.7±0.0359(n=3) | 4.74±0.0809(n=3) |
| app_goodput_sustentado_kbps | 40 | 6.55±0.0906(n=3) | 6.28±0.0699(n=3) | 6.44±0.0954(n=3) |
| app_goodput_sustentado_kbps | 50 | 8.08±0.177(n=3) | 7.7±0.152(n=3) | 7.77±0.288(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| app_msgs_total | 10 | 660.0±0(n=3) | 640.0±34.6(n=3) | 660.0±0(n=3) |
| app_msgs_total | 20 | 1380.0±0(n=3) | 1273.3±23.1(n=3) | 1380.0±0(n=3) |
| app_msgs_total | 30 | 2020.0±34.6(n=3) | 1913.3±11.5(n=3) | 1920.0±60(n=3) |
| app_msgs_total | 40 | 2660.0±34.6(n=3) | 2560.0±34.6(n=3) | 2620.0±34.6(n=3) |
| app_msgs_total | 50 | 3280.0±91.7(n=3) | 3140.0±69.3(n=3) | 3180.0±103.9(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| app_perda_pct | 10 | 0±0(n=3) | 3.33±1.46(n=3) | 0±0(n=3) |
| app_perda_pct | 20 | 0±0(n=3) | 4.41±0.882(n=3) | 0±0(n=3) |
| app_perda_pct | 30 | 0±0(n=3) | 2.3±0.416(n=3) | 0±0(n=3) |
| app_perda_pct | 40 | 0±0(n=3) | 2.01±0.295(n=3) | 0±0(n=3) |
| app_perda_pct | 50 | 0±0(n=3) | 1.3±0.965(n=3) | 0±0(n=3) |


## Deteccao

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| det_acuracia_pct | 10 | 80.9±0(n=3) | 80.9±0(n=3) | 80.9±0(n=3) |
| det_acuracia_pct | 20 | 80.9±0(n=3) | 80.9±0(n=3) | 80.9±0(n=3) |
| det_acuracia_pct | 30 | 81.1±0.283(n=3) | 80.9±0.137(n=3) | 80.9±0.183(n=3) |
| det_acuracia_pct | 40 | 80.8±0.171(n=3) | 80.9±0.04(n=3) | 80.8±0.0252(n=3) |
| det_acuracia_pct | 50 | 81.4±0.0737(n=3) | 81.1±0.225(n=3) | 81.3±0.115(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| det_classe_0_taxa_pct | 10 | 77.3±0(n=3) | 77.3±0(n=3) | 77.3±0(n=3) |
| det_classe_0_taxa_pct | 20 | 83±0(n=3) | 83±0(n=3) | 83±0(n=3) |
| det_classe_0_taxa_pct | 30 | 87.8±0.165(n=3) | 88.1±0.704(n=3) | 88.8±0.0924(n=3) |
| det_classe_0_taxa_pct | 40 | 83.9±0.249(n=3) | 83.5±0.294(n=3) | 83.6±0.354(n=3) |
| det_classe_0_taxa_pct | 50 | 84±0.179(n=3) | 83.4±0.167(n=3) | 83.4±0.972(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| det_classe_1_taxa_pct | 10 | 61±0(n=3) | 61±0(n=3) | 61±0(n=3) |
| det_classe_1_taxa_pct | 20 | 52.6±0(n=3) | 52.6±0(n=3) | 52.6±0(n=3) |
| det_classe_1_taxa_pct | 30 | 52.9±0.375(n=3) | 52.4±0.26(n=3) | 52.2±0.696(n=3) |
| det_classe_1_taxa_pct | 40 | 56±0.595(n=3) | 55.9±0.289(n=3) | 56±0.49(n=3) |
| det_classe_1_taxa_pct | 50 | 57.2±0.335(n=3) | 56.8±0.845(n=3) | 56.9±0.48(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| det_classe_2_taxa_pct | 10 | 44.8±0(n=3) | 44.8±0(n=3) | 44.8±0(n=3) |
| det_classe_2_taxa_pct | 20 | 53.9±0(n=3) | 53.9±0(n=3) | 53.9±0(n=3) |
| det_classe_2_taxa_pct | 30 | 55.9±1.45(n=3) | 56.2±0.866(n=3) | 54.5±3.01(n=3) |
| det_classe_2_taxa_pct | 40 | 54.2±0.221(n=3) | 54.6±0.346(n=3) | 54.3±0.495(n=3) |
| det_classe_2_taxa_pct | 50 | 54.3±1.31(n=3) | 54.7±0.212(n=3) | 54.6±0.414(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| det_classe_3_taxa_pct | 10 | 100.0±0(n=3) | 100.0±0(n=3) | 100.0±0(n=3) |
| det_classe_3_taxa_pct | 20 | 99.6±0(n=3) | 99.6±0(n=3) | 99.6±0(n=3) |
| det_classe_3_taxa_pct | 30 | 99.5±0.159(n=3) | 99.6±0.165(n=3) | 99.6±0.167(n=3) |
| det_classe_3_taxa_pct | 40 | 99.6±0.00577(n=3) | 99.8±0.00577(n=3) | 99.7±0.139(n=3) |
| det_classe_3_taxa_pct | 50 | 99±0.106(n=3) | 99.1±0.18(n=3) | 99.1±0.0321(n=3) |


## Rede

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| sta_rssi_media_dbm | 10 | -46.7±0.624(n=3) | -46.5±0.231(n=3) | -46.7±0.404(n=3) |
| sta_rssi_media_dbm | 20 | -47.1±0.05(n=3) | -46.7±0.551(n=3) | -46.4±0.333(n=3) |
| sta_rssi_media_dbm | 30 | -46.9±0.127(n=3) | -46.7±0.0962(n=3) | -47±0.158(n=3) |
| sta_rssi_media_dbm | 40 | -46.9±0.075(n=3) | -46.7±0.188(n=3) | -46.9±0.309(n=3) |
| sta_rssi_media_dbm | 50 | -46.6±0.203(n=3) | -46.8±0.0721(n=3) | -46.8±0.0416(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| sta_bitrate_media_mbps | 10 | 49.5±0(n=3) | 47.2±0.0748(n=3) | 46.2±0.32(n=3) |
| sta_bitrate_media_mbps | 20 | 50.7±0.132(n=3) | 48.1±0.0251(n=3) | 47.8±0.505(n=3) |
| sta_bitrate_media_mbps | 30 | 50.5±0.175(n=3) | 48.1±0.271(n=3) | 46.4±0.715(n=3) |
| sta_bitrate_media_mbps | 40 | 50.5±0.106(n=3) | 47.9±0.498(n=3) | 47.7±0.666(n=3) |
| sta_bitrate_media_mbps | 50 | 49.7±1.06(n=3) | 48.8±0.258(n=3) | 47±1.47(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| sta_retries | 10 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_retries | 20 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_retries | 30 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_retries | 40 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_retries | 50 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| sta_failed | 10 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_failed | 20 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_failed | 30 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_failed | 40 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_failed | 50 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| sta_beacon_loss | 10 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_beacon_loss | 20 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_beacon_loss | 30 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_beacon_loss | 40 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |
| sta_beacon_loss | 50 | 0±0(n=3) | 0±0(n=3) | 0±0(n=3) |


## Broker

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| broker_clients | 10 | 14±0(n=3) | 3±0(n=3) | 3±0(n=3) |
| broker_clients | 20 | 24±0(n=3) | 3±0(n=3) | 3±0(n=3) |
| broker_clients | 30 | 33.7±0.577(n=3) | 3±0(n=3) | 3±0(n=3) |
| broker_clients | 40 | 43.7±0.577(n=3) | 3±0(n=3) | 3±0(n=3) |
| broker_clients | 50 | 53.3±1.15(n=3) | 3±0(n=3) | 3±0(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| broker_rx_kbps | 10 | 1.73±4.12e-05(n=3) | 1.6±9.56e-05(n=3) | 1.6±0.000203(n=3) |
| broker_rx_kbps | 20 | 3.47±9.53e-05(n=3) | 3.2±0.000166(n=3) | 3.2±0.000255(n=3) |
| broker_rx_kbps | 30 | 5.16±0.1(n=3) | 4.8±0.0153(n=3) | 4.63±0.0861(n=3) |
| broker_rx_kbps | 40 | 6.9±0.0997(n=3) | 6.39±0.00898(n=3) | 6.35±0.123(n=3) |
| broker_rx_kbps | 50 | 8.15±1.21(n=3) | 7.9±0.035(n=3) | 7.72±0.281(n=3) |

| metrica | carga | mqtt | http | coap |
| --- | --- | --- | --- | --- | --- |
| broker_tx_kbps | 10 | 6.21±0.000124(n=3) | 4.67±0.0587(n=3) | 4.8±0.00061(n=3) |
| broker_tx_kbps | 20 | 11.4±0.00219(n=3) | 9.21±0.0808(n=3) | 9.6±0.000764(n=3) |
| broker_tx_kbps | 30 | 16.5±0.294(n=3) | 14±0.00324(n=3) | 13.9±0.258(n=3) |
| broker_tx_kbps | 40 | 21.7±0.296(n=3) | 18.9±0.0773(n=3) | 19±0.368(n=3) |
| broker_tx_kbps | 50 | 25.4±3.68(n=3) | 23.3±0.317(n=3) | 23.2±0.844(n=3) |
