/*
 * memoria.h - parametros e calibracao na EEPROM
 *
 * Baseado no EVA-RT 1.2.2 (c) 2025 EXOTIC TEAM MX, licenca AGPL-3.0
 */
#pragma once

#include "linha.h"
#include "params.h"

bool memCarregarParametros(Parametros &p);   // false = nada valido gravado
void memSalvarParametros(const Parametros &p);

// A calibracao vale so para o mapa da barra e a cor de linha com que foi feita
bool memCarregarCalibracao(Calibracao &c);
void memSalvarCalibracao(const Calibracao &c);
