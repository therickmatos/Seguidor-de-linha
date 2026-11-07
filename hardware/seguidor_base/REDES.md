# Redes da placa base (conferência da importação KiCad → EasyEDA)

_Gerado por `ferramentas/esquematico/redes.py` a partir da netlist do `seguidor_base.kicad_sch` (rev 1.0). Depois de importar o esquemático no EasyEDA Pro, conferir rede por rede. Formato: `REF.pino (nome do pino)`. Valores e encapsulamentos em `BOM_seguidor_base.csv`._

**53 redes**, **7 pinos sem ligação**.

**Atenção na importação:**
- No símbolo do ATmega (U2), os pinos 5 e 21 (GND) e 6 (VCC) estão escondidos e empilhados sobre os pinos 3 e 4; no KiCad eles se ligam pela posição. Conferir no EasyEDA se U2.5 e U2.21 estão no GND e U2.6 no +5V.
- `VBAT`, `+5V` e `GND` vêm de símbolos de alimentação (ligação pelo nome): conferir que chegaram com esses nomes.

| Rede | Pinos | Qtd |
|---|---|---|
| `VBAT` | C1.1, C2.1, C3.1, C11.1, C13.1, C14.1, C16.1, C17.1, D1.1 (K), J1.1, M3.1 (+), R2.1, U1.1 (VI), U3.11 (VM), U4.11 (VM) | 15 |
| `+5V` | C4.1, C5.1, C7.1, J2.1, J3.1, J4.5, J5.2 (VCC), R1.1, R4.1, R7.1, R10.1, R11.1, R13.1, R19.1, S1.3, S2.3, U1.3 (VO), U2.4 (VCC), U2.6 (VCC), U2.18 (AVCC) | 20 |
| `GND` | C1.2, C2.2, C3.2, C4.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C13.2, C16.2, C17.2, J1.2, J2.2, J3.2, J4.4, J5.6 (GND), LED1.1 (K), LED2.1 (K), LED3.1 (K), LED4.1 (K), Q1.2 (S), R3.2, R5.2, R8.2, R12.2, R14.2, R15.2, R17.2, R21.2, S1.2 (K), S2.2 (K), SW1.1, SW2.2, SW3.2, U1.2 (GND), U2.3 (GND), U2.5 (GND), U2.21 (GND), U3.7 (IMODE), U3.9 (PGND), U3.15 (GND), U3.16 (PMODE), U3.17 (PAD), U4.7 (IMODE), U4.9 (PGND), U4.15 (GND), U4.16 (PMODE), U4.17 (PAD) | 50 |
| `AREF` | C8.1, U2.20 (AREF) | 2 |
| `B1_D11` | J5.4 (MOSI), SW2.1, U2.15 (PB3) | 3 |
| `B2_D12` | J5.1 (MISO), SW3.1, U2.16 (PB4) | 3 |
| `BT_RXD` | J4.2, R20.2, R21.1 | 3 |
| `BT_TXD` | J4.3, R22.2 | 2 |
| `C0_A4` | J2.4, U2.27 (PC4) | 2 |
| `CPH_A` | C12.1, U3.13 (CPH) | 2 |
| `CPH_B` | C15.1, U4.13 (CPH) | 2 |
| `CPL_A` | C12.2, U3.14 (CPL) | 2 |
| `CPL_B` | C15.2, U4.14 (CPL) | 2 |
| `DIRA_D3` | U2.1 (PD3), U3.2 (PH/IN2) | 2 |
| `DIRB_D4` | U2.2 (PD4), U4.2 (PH/IN2) | 2 |
| `DRV_SLEEP` | R13.2, U3.3 (nSLEEP), U4.3 (nSLEEP) | 3 |
| `DTR` | C18.1, J3.5 | 2 |
| `IPROPI_A` | R14.1, U3.6 (IPROPI) | 2 |
| `IPROPI_B` | R15.1, U4.6 (IPROPI) | 2 |
| `LEDA_D2` | R6.1, U2.32 (PD2) | 2 |
| `LEDB_D7` | R9.1, U2.11 (PD7) | 2 |
| `LEDC_D13` | J5.3 (SCK), R18.1, U2.17 (PB5) | 3 |
| `MARK_L_A5` | R5.1, S1.4, U2.28 (PC5) | 3 |
| `MARK_R_A6` | R8.1, S2.4, U2.19 (ADC6) | 3 |
| `Net-(LED1-A)` | LED1.2 (A), R1.2 | 2 |
| `Net-(LED2-A)` | LED2.2 (A), R6.2 | 2 |
| `Net-(LED3-A)` | LED3.2 (A), R9.2 | 2 |
| `Net-(LED4-A)` | LED4.2 (A), R18.2 | 2 |
| `Net-(LED5-A)` | LED5.2 (A), R19.2 | 2 |
| `Net-(Q1-G)` | Q1.1 (G), R16.2, R17.1 | 3 |
| `Net-(S1-A)` | R4.2, S1.1 (A) | 2 |
| `Net-(S2-A)` | R7.2, S2.1 (A) | 2 |
| `OUT_A1` | M1.2 (-), U3.8 (OUT1) | 2 |
| `OUT_A2` | M1.1 (+), U3.10 (OUT2) | 2 |
| `OUT_B1` | M2.2 (-), U4.8 (OUT1) | 2 |
| `OUT_B2` | M2.1 (+), U4.10 (OUT2) | 2 |
| `OUT_C` | D1.2 (A), M3.2 (-), Q1.3 (D) | 3 |
| `PWMA_D5` | U2.9 (PD5), U3.1 (EN/IN1) | 2 |
| `PWMB_D6` | U2.10 (PD6), U4.1 (EN/IN1) | 2 |
| `PWMC_D10` | R16.1, U2.14 (PB2) | 2 |
| `RESET` | C18.2, J5.5 (~{RST}), R10.2, SW1.2, U2.29 (~{RESET}/PC6) | 5 |
| `RX_D0` | J3.3, R22.1, U2.30 (PD0) | 3 |
| `S0_A0` | J2.8, U2.23 (PC0) | 2 |
| `S1_A1` | J2.7, U2.24 (PC1) | 2 |
| `S2_A2` | J2.6, U2.25 (PC2) | 2 |
| `S3_A3` | J2.5, U2.26 (PC3) | 2 |
| `TX_D1` | J3.4, LED5.1 (K), R20.1, U2.31 (PD1) | 4 |
| `VBAT_A7` | C6.1, R2.2, R3.1, U2.22 (ADC7) | 4 |
| `VCP_A` | C11.2, U3.12 (VCP) | 2 |
| `VCP_B` | C14.2, U4.12 (VCP) | 2 |
| `VREF` | R11.2, R12.1, U3.5 (VREF), U4.5 (VREF) | 4 |
| `XTAL1` | C9.1, U2.7 (XTAL1/PB6), X1.1 | 3 |
| `XTAL2` | C10.1, U2.8 (XTAL2/PB7), X1.2 | 3 |

## Pinos sem ligação (marcados com X)

- J2.3 — BARRA (1x8, 2,54 mm)
- J4.1 — BLUETOOTH (femea 1x6, ordem HC-05)
- J4.6 — BLUETOOTH (femea 1x6, ordem HC-05)
- U2.12 (PB0) — ATmega328P-AU
- U2.13 (PB1) — ATmega328P-AU
- U3.4 (nFAULT) — DRV8874PWPR
- U4.4 (nFAULT) — DRV8874PWPR
