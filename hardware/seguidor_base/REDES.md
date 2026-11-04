# Redes da placa base (referência para o port KiCad → EasyEDA)

_Gerado da netlist do esquemático KiCad rev 1.0 (`kicad/seguidor_base.kicad_sch`). Depois de passar o esquemático para o EasyEDA Pro, conferir rede por rede. Formato: `REF.pino (nome do pino)`. Valores e encapsulamentos em `BOM_seguidor_base.csv`._

**54 redes**, **7 pinos sem ligação**.

| Rede | Pinos | Qtd |
|---|---|---|
| `VBAT` | C1.1, C2.1, C3.1, C6.1, C7.1, C8.1, C13.1, C15.1, D1.1 (K), J1.1, M3.1 (+), R23.1, U2.11 (VM), U3.11 (VM), U5.1 (VI) | 15 |
| `+5V` | C4.1, C5.1, C9.1, J2.1, J3.1, J4.5, J5.2 (VCC), J8.1, J9.1, R1.1, R2.1, R3.1, R10.1, R13.1, R15.1, R20.1, R21.1, S0.3, S1.3, U1.4 (VCC), U1.6 (VCC), U1.18 (AVCC), U5.3 (VO) | 23 |
| `GND` | C1.2, C2.2, C3.2, C4.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C18.2, J1.2, J2.2, J3.2, J4.4, J5.6 (GND), J8.2, J9.2, LED1.1 (K), LED2.1 (K), LED4.1 (K), LED5.1 (K), Q1.2 (S), R8.2, R11.2, R12.2, R14.2, R17.2, R24.2, R30.2, R31.2, S0.2 (K), S1.2 (K), SW0.1, SW1.2, SW2.2, U1.3 (GND), U1.5 (GND), U1.21 (GND), U2.7 (IMODE), U2.9 (PGND), U2.15 (GND), U2.16 (PMODE), U2.17 (PAD), U3.7 (IMODE), U3.9 (PGND), U3.15 (GND), U3.16 (PMODE), U3.17 (PAD), U5.2 (GND) | 52 |
| `AREF` | C10.1, U1.20 (AREF) | 2 |
| `B1_D11` | J5.4 (MOSI), SW1.1, U1.15 (PB3) | 3 |
| `B2_D12` | J5.1 (MISO), SW2.1, U1.16 (PB4) | 3 |
| `BT_RXD` | J4.2, R16.2, R17.1 | 3 |
| `BT_TXD` | J4.3, R18.2 | 2 |
| `C0_A4` | J2.4, U1.27 (PC4) | 2 |
| `CPH_A` | C14.1, U2.13 (CPH) | 2 |
| `CPH_B` | C16.1, U3.13 (CPH) | 2 |
| `CPL_A` | C14.2, U2.14 (CPL) | 2 |
| `CPL_B` | C16.2, U3.14 (CPL) | 2 |
| `DIRA_D3` | U1.1 (PD3), U2.2 (PH/IN2) | 2 |
| `DIRB_D4` | U1.2 (PD4), U3.2 (PH/IN2) | 2 |
| `DRV_SLEEP` | R15.2, U2.3 (nSLEEP), U3.3 (nSLEEP) | 3 |
| `DTR` | C17.1, J3.5 | 2 |
| `IPROPI_A` | R11.1, U2.6 (IPROPI) | 2 |
| `IPROPI_B` | R12.1, U3.6 (IPROPI) | 2 |
| `LEDA_D2` | J8.4, R6.1, U1.32 (PD2) | 3 |
| `LEDB_D7` | J9.4, R7.1, U1.11 (PD7) | 3 |
| `LEDC_D13` | J5.3 (SCK), R5.1, U1.17 (PB5) | 3 |
| `MARK_L_A5` | J8.3, R30.1, S0.4, U1.28 (PC5) | 4 |
| `MARK_R_A6` | J9.3, R31.1, S1.4, U1.19 (ADC6) | 4 |
| `Net-(LED1-A)` | LED1.2 (A), R6.2 | 2 |
| `Net-(LED2-A)` | LED2.2 (A), R7.2 | 2 |
| `Net-(LED4-A)` | LED4.2 (A), R5.2 | 2 |
| `Net-(LED5-A)` | LED5.2 (A), R10.2 | 2 |
| `Net-(LED6-A)` | LED6.2 (A), R1.2 | 2 |
| `Net-(LED7-A)` | LED7.2 (A), R2.2 | 2 |
| `Net-(Q1-G)` | Q1.1 (G), R8.1, R9.2 | 3 |
| `Net-(S0-A)` | R20.2, S0.1 (A) | 2 |
| `Net-(S1-A)` | R21.2, S1.1 (A) | 2 |
| `OUT_A1` | M1.2 (-), U2.8 (OUT1) | 2 |
| `OUT_A2` | M1.1 (+), U2.10 (OUT2) | 2 |
| `OUT_B1` | M2.2 (-), U3.8 (OUT1) | 2 |
| `OUT_B2` | M2.1 (+), U3.10 (OUT2) | 2 |
| `OUT_C` | D1.2 (A), M3.2 (-), Q1.3 (D) | 3 |
| `PWMA_D5` | U1.9 (PD5), U2.1 (EN/IN1) | 2 |
| `PWMB_D6` | U1.10 (PD6), U3.1 (EN/IN1) | 2 |
| `PWMC_D10` | R9.1, U1.14 (PB2) | 2 |
| `RESET` | C17.2, J5.5 (~{RST}), R3.2, SW0.2, U1.29 (~{RESET}/PC6) | 5 |
| `RX_D0` | J3.3, LED7.1 (K), R18.1, U1.30 (PD0) | 4 |
| `S0_A0` | J2.8, U1.23 (PC0) | 2 |
| `S1_A1` | J2.7, U1.24 (PC1) | 2 |
| `S2_A2` | J2.6, U1.25 (PC2) | 2 |
| `S3_A3` | J2.5, U1.26 (PC3) | 2 |
| `TX_D1` | J3.4, LED6.1 (K), R16.1, U1.31 (PD1) | 4 |
| `VBAT_A7` | C18.1, R23.2, R24.1, U1.22 (ADC7) | 4 |
| `VCP_A` | C13.2, U2.12 (VCP) | 2 |
| `VCP_B` | C15.2, U3.12 (VCP) | 2 |
| `VREF` | R13.2, R14.1, U2.5 (VREF), U3.5 (VREF) | 4 |
| `XTAL1` | C11.1, U1.7 (XTAL1/PB6), X1.1 | 3 |
| `XTAL2` | C12.1, U1.8 (XTAL2/PB7), X1.2 | 3 |

## Pinos sem ligação (marcados com X)

- J2.3 — BARRA (1x8, 2,54 mm)
- J4.1 — BLUETOOTH (femea 1x6, ordem HC-05)
- J4.6 — BLUETOOTH (femea 1x6, ordem HC-05)
- U1.12 (PB0) — ATmega328P-AU
- U1.13 (PB1) — ATmega328P-AU
- U2.4 (nFAULT) — DRV8874PWPR
- U3.4 (nFAULT) — DRV8874PWPR
