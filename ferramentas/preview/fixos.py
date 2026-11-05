"""Posicoes fixas e sequencia de busca (regras + correcoes do coordenador)."""
import footprints as F

def primeiro(P, colocar):
    F.REF_FOOTPRINT["J1"] = "XT30_RABICHO"      # XT30PW-M nao cabe no antigo VIN
    F.REF_FOOTPRINT["X1"] = "CRISTAL_3225_4P"   # HC-49/S (3,5 mm) nao cabe sob a bateria
    fixos = [
        ("C1", -22.00, 2.06, -90, None, "EVA-RT mantido (eletrolitico entre os pes da carcaca)"),
        ("C2", 21.50, 2.06, 90, None, "mudou 0,5 mm (era x 22,0): libera o Q1 entre C2 e a ventoinha"),
        ("C3", -19.18, 7.00, 90, None, "EVA-RT mantido"),
        ("C4", -24.26, 10.12, 90, None, "EVA-RT mantido"),
        ("C5", -21.72, 8.00, -90, None, "EVA-RT mantido (tantalo)"),
        ("U5", -30.61, 9.02, 180, None, "EVA-RT mantido (78M05)"),
        ("LED5", -21.34, 13.46, 0, None, "EVA-RT mantido (indica 5 V)"),
        ("R10", -17.91, 11.81, 0, None, "EVA-RT mantido"),
        ("LED4", 21.34, 13.46, 180, None, "EVA-RT mantido (LED C, vermelho)"),
        ("R5", 18.67, 10.79, 90, None, "EVA-RT mantido"),
        ("R8", 20.57, 7.62, -90, None, "EVA-RT mantido (pull-down do gate)"),
        ("R9", 20.57, 10.79, -90, None, "EVA-RT mantido (200 ohm do gate)"),
        ("LED6", -11.94, -21.46, 180, None, "EVA-RT mantido (TX)"),
        ("R1", -15.49, -21.46, 0, None, "EVA-RT mantido"),
        ("LED7", -11.94, -23.37, 180, None, "EVA-RT mantido (RX, opcional)"),
        ("R2", -15.49, -23.37, 0, None, "EVA-RT mantido (opcional)"),
        ("R3", -15.49, -19.56, 0, None, "EVA-RT mantido (10k do RESET)"),
        ("U1", 0.00, -23.00, -45, None, "EVA-RT mantido: (0;-18) invade o disco da ventoinha"),
        ("U2", -22.10, -12.45, -90, None, "DRV8874 motor esq. no lugar do IFX_A1; potencia (8-11) para o motor"),
        ("U3", 22.10, -12.45, 90, None, "DRV8874 motor dir. no lugar do IFX_B1; potencia (8-11) para o motor"),
        ("M1", -36.58, 1.27, 0, None, "motor esq.: pads nas posicoes do EVA-RT"),
        ("M2", 36.58, 1.27, 0, None, "motor dir.: pads nas posicoes do EVA-RT"),
        ("M3", 29.72, 3.05, 0, None, "ventoinha: pads nas posicoes do EVA-RT"),
        ("J2", 0.00, 22.74, 0, None, "barra de sensores 1x8, linha y 22,74"),
        ("J3", 9.00, -28.75, 0, None, "gravacao 1x5, rot 0, pontas para -y; x = 9,0 (proposta: velcro 2,2 mm para fora)"),
        ("J4", 33.00, 7.05, 0, None, "BT femea 1x6 (pino 1 em y 0,7, pino 6 em y 13,4); x = 33,0 (corpo do socket nao cruza o M3)"),
        ("J5", 35.244, -10.901, 0, "BOTTOM", "ICSP: posicoes do EVA-RT (face BOTTOM)"),
        ("LED1", -69.5, 4.5, -90, None, "sensor esq.: LED sobre o QRE (braco integrado)"),
        ("LED2", 69.5, 4.5, 90, None, "sensor dir.: LED sobre o QRE (braco integrado)"),
        ("S0", -69.5, 4.5, 180, "BOTTOM", "QRE1113GR esq. (curva, A5) no braco"),
        ("S1", 69.5, 4.5, 0, "BOTTOM", "QRE1113GR dir. (partida/chegada, A6) no braco"),
        ("SW1", 27.00, 10.70, 90, None, "BOTAO 1: frente direita, fora da succao (rot 90)"),
    ]
    for ref, x, y, rot, lado, motivo in fixos:
        colocar(ref, x, y, rot, lado, motivo)
    colocar("J8", -45.044, 4.51, 0, None, "DNP: asa esq. (pode apagar no layout)", dnp=True)
    colocar("J9", 45.044, 4.51, 0, None, "DNP: asa dir. (pode apagar no layout)", dnp=True)

def satelites(P, colocar, satelite, ancora, buscar, custo, pad_xy):
    pxy = pad_xy
    def mid(*pts):
        return float(sum(p[0] for p in pts) / len(pts)), float(sum(p[1] for p in pts) / len(pts))
    R4 = [0, 90, 180, 270]
    R8 = [0, 90, 180, 270, 45, 135, 225, 315]
    # 1) botoes de zona lateral e J1
    satelite("SW2", 26.90, -20.50, 2.5, [90, 0], motivo="BOTAO 2: traseira direita, fora da succao")
    satelite("SW0", -26.90, -20.50, 0.0, [90], motivo="RESET: traseira esquerda, separado dos botoes 1 e 2")
    satelite("J1", -28.60, 0.0, 3.0, [90, 0], motivo="bateria XT30 rabicho: lateral esquerda (no lugar do VIN nao coube)")
    # 2) ventoinha
    satelite("C8", *pxy("M3", 1), 4.0, R4, alvo=[pxy("M3", 1)], modo="min", motivo="100 nF do VBAT (perto do VBAT da ventoinha)")
    satelite("Q1", *pxy("M3", 2), 6.0, R4, lado="BOTTOM", alvo=[pxy("M3", 2)], modo="min", motivo="MOSFET da ventoinha: face BOTTOM (sem colisao com THT)")
    satelite("D1", *mid(pxy("M3", 1), pxy("M3", 2)), 4.0, R4, alvo=[pxy("M3", 1), pxy("M3", 2)], modo="soma", motivo="roda livre da ventoinha (catodo no VBAT)")
    # 2b) VCC do ATmega primeiro (regra <= 2 mm)
    satelite("C9", -3.55, -27.15, 2.0, R8, alvo=[pxy("U1", 4), pxy("U1", 6)], modo="min", motivo="100 nF do VCC (U1.4/U1.6): <= 2 mm do pino")
    satelite("C10", *pxy("U1", 20), 3.0, R4, alvo=[pxy("U1", 20)], modo="min", motivo="100 nF do AREF (U1.20): <= 2 mm do pino")
    # 3) cristal e capacitores (3225 sob a bateria; HC-49/S nao cabe la)
    satelite("X1", -8.0, -27.5, 2.5, [0, 90, 180, 270], alvo=[pxy("U1", 7), pxy("U1", 8)], modo="soma", motivo="cristal 16 MHz (3225 sob a bateria, 0,8 mm)")
    satelite("C11", *mid(pxy("U1", 7), pxy("X1", 1)), 5.0, R8, alvo=[pxy("U1", 7), pxy("X1", 1)], modo="soma", motivo="22 pF do XTAL1")
    satelite("C12", *mid(pxy("U1", 8), pxy("X1", 3)), 6.0, R8, alvo=[pxy("U1", 8), pxy("X1", 3)], modo="soma", motivo="22 pF do XTAL2")
    satelite("C17", *mid(pxy("J3", 5), pxy("U1", 29)), 6.0, R4, alvo=[pxy("J3", 5), pxy("U1", 29)], modo="soma", motivo="DTR -> RESET (auto-reset)")
    # 4) drivers DRV8874
    # capacitores dos DRV8874 (busca pelos pinos-alvo)
    satelite("C6", *pxy("U2", 11), 4.0, R4, alvo=[pxy("U2", 11)], modo="min", motivo="VM: junto ao pino 11 (U2)")
    satelite("C7", *pxy("U3", 11), 4.0, R4, alvo=[pxy("U3", 11)], modo="min", motivo="VM: junto ao pino 11 (U3)")
    satelite("C13", *pxy("U2", 12), 4.0, R4, alvo=[pxy("U2", 12)], modo="min", motivo="VCP -> VM (U2)")
    satelite("C15", *pxy("U3", 12), 4.0, R4, alvo=[pxy("U3", 12)], modo="min", motivo="VCP -> VM (U3)")
    satelite("C14", *mid(pxy("U2", 13), pxy("U2", 14)), 4.0, R4, alvo=[pxy("U2", 13), pxy("U2", 14)], modo="soma", motivo="CPH-CPL (U2)")
    satelite("C16", *mid(pxy("U3", 13), pxy("U3", 14)), 4.0, R4, alvo=[pxy("U3", 13), pxy("U3", 14)], modo="soma", motivo="CPH-CPL (U3)")
    satelite("R11", *pxy("U2", 6), 3.0, R4, alvo=[pxy("U2", 6)], modo="min", motivo="IPROPI (U2): limite de corrente")
    satelite("R12", *pxy("U3", 6), 3.0, R4, alvo=[pxy("U3", 6)], modo="min", motivo="IPROPI (U3): limite de corrente")
    satelite("R13", *mid(pxy("U2", 5), pxy("U3", 5)), 9.0, R4, alvo=[pxy("U2", 5), pxy("U3", 5)], modo="soma", motivo="VREF divisor (comum aos DRV)")
    satelite("R14", *mid(pxy("U2", 5), pxy("U3", 5)), 9.0, R4, alvo=[pxy("U2", 5), pxy("U3", 5)], modo="soma", motivo="VREF divisor (comum aos DRV)")
    satelite("R15", *mid(pxy("U2", 3), pxy("U3", 3)), 9.0, R4, alvo=[pxy("U2", 3), pxy("U3", 3)], modo="soma", motivo="nSLEEP (comum aos DRV)")
    # 5) medicao da bateria e Bluetooth
    for ref in ("R23", "R24", "C18"):
        satelite(ref, *pxy("U1", 22), 6.0, R4, alvo=[pxy("U1", 22)], modo="min", motivo="medicao VBAT (opcional)")
    satelite("R16", *pxy("J4", 2), 5.0, R4, alvo=[pxy("J4", 2)], modo="min", motivo="divisor 5 V -> 3,3 V (TX)")
    satelite("R17", *pxy("J4", 2), 5.0, R4, alvo=[pxy("J4", 2)], modo="min", motivo="divisor 5 V -> 3,3 V (BT_RXD)")
    satelite("R18", *pxy("J4", 3), 5.0, R4, alvo=[pxy("J4", 3)], modo="min", motivo="0 ohm RX -> BT_TXD")
    # 6) sensores de marca (braco integrado)
    satelite("R20", *pxy("S0", 1), 3.0, R4, lado="BOTTOM", alvo=[pxy("S0", 1)], modo="min", motivo="LED do QRE esq. (BOTTOM)")
    satelite("R30", *pxy("S0", 4), 5.0, R4, lado="BOTTOM", alvo=[pxy("S0", 4)], modo="min", motivo="pull-down do A5 (BOTTOM)")
    satelite("R21", *pxy("S1", 1), 3.0, R4, lado="BOTTOM", alvo=[pxy("S1", 1)], modo="min", motivo="LED do QRE dir. (BOTTOM)")
    satelite("R31", *pxy("S1", 4), 5.0, R4, lado="BOTTOM", alvo=[pxy("S1", 4)], modo="min", motivo="pull-down do A6 (BOTTOM)")
    satelite("R6", *pxy("LED1", 2), 3.0, R4, alvo=[pxy("LED1", 2)], modo="min", motivo="resistor do LED esq. (TOP)")
    satelite("R7", *pxy("LED2", 2), 3.0, R4, alvo=[pxy("LED2", 2)], modo="min", motivo="resistor do LED dir. (TOP)")
