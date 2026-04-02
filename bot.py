import requests
import time
import math
from datetime import datetime, timezone

# ================= TELEGRAM =================
TOKEN = "8772294732:AAGU62SChVJfmwf9RpweG-inBGAjIDlMwms"
CHAT_ID = "5019372975"

def enviar_alerta(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

# ================= CONFIG =================
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "MATICUSDT"]

CAPITAL_BASE      = 100.0   # Capital referencia en USDT para calcular tamaño
RIESGO_PCT        = 0.01    # Riesgo por operación: 1% del capital
SCORE_MIN_LONG    = 9       # Score mínimo para long
SCORE_MIN_SHORT   = 9       # Score mínimo para short
COOLDOWN_SYMBOL   = 300     # Segundos entre operaciones del mismo símbolo
RESUMEN_CADA      = 3600    # Enviar resumen cada N segundos

estado            = False
direccion         = None    # "long" o "short"
entrada           = 0.0
max_precio        = 0.0
min_precio        = float("inf")
symbol_activo     = None

racha_perdidas    = 0
racha_ganancias   = 0
ganancia_acumulada = 0.0
operaciones_totales = 0
operaciones_ganadoras = 0
pnl_total         = 0.0

cooldowns         = {}      # {symbol: timestamp_ultima_salida}
ultimo_resumen    = time.time()

enviar_alerta(
    "📊 <b>BOT CUANTITATIVO v3 ACTIVO</b>\n"
    f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
    f"💼 Capital ref: ${CAPITAL_BASE} | Riesgo/op: {RIESGO_PCT*100:.1f}%\n"
    f"📈 Long + 📉 Short habilitados"
)

# ================= DATOS =================

def get_klines(symbol, interval, limit=60):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url, timeout=10).json()
    cierres   = [float(x[4]) for x in r]
    altos     = [float(x[2]) for x in r]
    bajos     = [float(x[3]) for x in r]
    volumenes = [float(x[5]) for x in r]
    aperturas = [float(x[1]) for x in r]
    return cierres, altos, bajos, volumenes, aperturas

# ================= INDICADORES =================

def ema(valores, n):
    k = 2 / (n + 1)
    e = [valores[0]]
    for v in valores[1:]:
        e.append(v * k + e[-1] * (1 - k))
    return e

def rsi(cierres, n=14):
    ganancias, perdidas = [], []
    for i in range(1, len(cierres)):
        d = cierres[i] - cierres[i-1]
        ganancias.append(max(d, 0))
        perdidas.append(max(-d, 0))
    if len(ganancias) < n:
        return 50.0
    ag = sum(ganancias[-n:]) / n
    ap = sum(perdidas[-n:]) / n
    if ap == 0:
        return 100.0
    return 100 - (100 / (1 + ag / ap))

def macd_completo(cierres):
    e12 = ema(cierres, 12)
    e26 = ema(cierres, 26)
    linea    = [a - b for a, b in zip(e12, e26)]
    senal    = ema(linea, 9)
    hist     = [l - s for l, s in zip(linea, senal)]
    return linea[-1], senal[-1], hist[-1], hist[-2] if len(hist) > 1 else 0

def atr(altos, bajos, cierres, n=14):
    trs = []
    for i in range(1, len(cierres)):
        trs.append(max(
            altos[i] - bajos[i],
            abs(altos[i] - cierres[i-1]),
            abs(bajos[i] - cierres[i-1])
        ))
    if len(trs) < n:
        return cierres[-1] * 0.002
    return sum(trs[-n:]) / n

def bollinger(cierres, n=20, dev=2.0):
    if len(cierres) < n:
        p = cierres[-1]
        return p, p * 1.01, p * 0.99
    v = cierres[-n:]
    m = sum(v) / n
    s = math.sqrt(sum((x - m)**2 for x in v) / n)
    return m, m + dev * s, m - dev * s

def stoch_rsi(cierres, n=14, smooth=3):
    rsis = [rsi(cierres[:i+1], n) for i in range(n, len(cierres))]
    if len(rsis) < n:
        return 50.0, 50.0
    ventana = rsis[-n:]
    mn, mx = min(ventana), max(ventana)
    if mx == mn:
        return 50.0, 50.0
    k = ((rsis[-1] - mn) / (mx - mn)) * 100
    d = sum(((rsis[-i] - mn) / (mx - mn)) * 100 for i in range(1, smooth + 1)) / smooth
    return k, d

def volumen_relativo(volumenes, n=20):
    if len(volumenes) < n:
        return 1.0
    promedio = sum(volumenes[-n:-1]) / (n - 1)
    if promedio == 0:
        return 1.0
    return volumenes[-1] / promedio

def obv(cierres, volumenes):
    resultado = [0.0]
    for i in range(1, len(cierres)):
        if cierres[i] > cierres[i-1]:
            resultado.append(resultado[-1] + volumenes[i])
        elif cierres[i] < cierres[i-1]:
            resultado.append(resultado[-1] - volumenes[i])
        else:
            resultado.append(resultado[-1])
    return resultado

def divergencia_alcista(cierres, n=14):
    if len(cierres) < 30:
        return False
    r_actual = rsi(cierres, n)
    r_previo = rsi(cierres[:-5], n)
    precio_baja = cierres[-1] < cierres[-6]
    rsi_sube    = r_actual > r_previo + 2
    return precio_baja and rsi_sube

def divergencia_bajista(cierres, n=14):
    if len(cierres) < 30:
        return False
    r_actual = rsi(cierres, n)
    r_previo = rsi(cierres[:-5], n)
    precio_sube = cierres[-1] > cierres[-6]
    rsi_baja    = r_actual < r_previo - 2
    return precio_sube and rsi_baja

def mercado_en_tendencia(cierres, umbral=0.3):
    e20 = ema(cierres, 20)
    e50 = ema(cierres, 50)
    diff = abs(e20[-1] - e50[-1]) / e50[-1]
    return diff > umbral * 0.01

def detectar_pullback_long(cierres):
    e9 = ema(cierres, 9)
    subida      = cierres[-6] < cierres[-5] < cierres[-4]
    retroceso   = cierres[-4] > cierres[-3] >= cierres[-2]
    retoma      = cierres[-1] > cierres[-2]
    soporte     = cierres[-1] >= e9[-1] * 0.999
    return subida and retroceso and retoma and soporte

def detectar_pullback_short(cierres):
    e9 = ema(cierres, 9)
    bajada      = cierres[-6] > cierres[-5] > cierres[-4]
    rebote      = cierres[-4] < cierres[-3] <= cierres[-2]
    retoma      = cierres[-1] < cierres[-2]
    resistencia = cierres[-1] <= e9[-1] * 1.001
    return bajada and rebote and retoma and resistencia

def patron_vela_alcista(cierres, altos, bajos, aperturas):
    o, c, h, l = aperturas[-1], cierres[-1], altos[-1], bajos[-1]
    rango = h - l
    if rango == 0:
        return False
    mecha_inf = (min(o, c) - l) / rango
    cuerpo    = (c - o) / rango
    return c > o and mecha_inf > 0.35 and cuerpo > 0.35

def patron_vela_bajista(cierres, altos, bajos, aperturas):
    o, c, h, l = aperturas[-1], cierres[-1], altos[-1], bajos[-1]
    rango = h - l
    if rango == 0:
        return False
    mecha_sup = (h - max(o, c)) / rango
    cuerpo    = (o - c) / rango
    return c < o and mecha_sup > 0.35 and cuerpo > 0.35

# ================= SESIÓN HORARIA =================

def sesion_activa():
    hora = datetime.now(timezone.utc).hour
    # Sesión asiática: 00-08 UTC — volatilidad media
    # Sesión europea: 07-16 UTC — buena volatilidad
    # Sesión americana: 13-21 UTC — mayor volatilidad
    # Evitar 22-23 UTC (cierre + bajo volumen)
    if 0 <= hora < 22:
        return True
    return False

def peso_sesion():
    hora = datetime.now(timezone.utc).hour
    if 13 <= hora < 21:   # Solapamiento EU + US: mejor momento
        return 1.0
    if 7 <= hora < 16:    # Solo europea
        return 0.85
    if 0 <= hora < 8:     # Solo asiática
        return 0.75
    return 0.6

# ================= SIZING DE POSICIÓN =================

def calcular_tamano(precio_entrada, sl, capital=CAPITAL_BASE, riesgo_pct=RIESGO_PCT):
    riesgo_usd = capital * riesgo_pct
    distancia  = abs(precio_entrada - sl)
    if distancia == 0:
        return 0
    unidades = riesgo_usd / distancia
    return round(unidades, 6)

# ================= RÉGIMEN DE MERCADO =================

def detectar_regimen(cierres_15m):
    e20 = ema(cierres_15m, 20)
    e50 = ema(cierres_15m, 50)
    adx_proxy = abs(e20[-1] - e50[-1]) / e50[-1] * 100
    if adx_proxy > 0.5:
        return "TENDENCIA"
    return "LATERAL"

# ================= SCORE LONG =================

def score_long(cierres, altos, bajos, volumenes, aperturas):
    s = 0
    info = {}

    e9  = ema(cierres, 9)
    e21 = ema(cierres, 21)
    e50 = ema(cierres, 50)

    info["EMA"]  = e9[-1] > e21[-1] > e50[-1]
    if info["EMA"]:
        s += 3

    slope_ok = e9[-1] > e9[-4] and e21[-1] > e21[-4]
    info["Slope"] = slope_ok
    if slope_ok:
        s += 1

    info["PB"] = detectar_pullback_long(cierres)
    if info["PB"]:
        s += 2

    r = rsi(cierres)
    info["RSI"] = r
    if 42 <= r <= 65:
        s += 2
    elif r > 72:
        s -= 2

    div_alc = divergencia_alcista(cierres)
    info["DivAlc"] = div_alc
    if div_alc:
        s += 2

    linea, senal, hist_act, hist_prev = macd_completo(cierres)
    info["MACD"] = linea > senal
    if linea > senal:
        s += 1
    info["MACDhist"] = hist_act > 0 and hist_act > hist_prev
    if hist_act > 0 and hist_act > hist_prev:
        s += 1

    vr = volumen_relativo(volumenes)
    info["Vol"] = vr
    if vr >= 1.3:
        s += 2
    elif vr >= 1.1:
        s += 1

    obv_vals = obv(cierres, volumenes)
    obv_sube = obv_vals[-1] > obv_vals[-5]
    info["OBV"] = obv_sube
    if obv_sube:
        s += 1

    bb_m, bb_sup, bb_inf = bollinger(cierres)
    if cierres[-1] > bb_m and cierres[-2] <= bb_m:
        s += 1
        info["BB"] = "cruce"
    elif cierres[-1] > bb_m:
        info["BB"] = "sobre"
    else:
        info["BB"] = "bajo"

    stk, std = stoch_rsi(cierres)
    info["StochRSI"] = stk
    if stk > std and 20 < stk < 80:
        s += 1

    info["Vela"] = patron_vela_alcista(cierres, altos, bajos, aperturas)
    if info["Vela"]:
        s += 1

    return s, info, r

# ================= SCORE SHORT =================

def score_short(cierres, altos, bajos, volumenes, aperturas):
    s = 0
    info = {}

    e9  = ema(cierres, 9)
    e21 = ema(cierres, 21)
    e50 = ema(cierres, 50)

    info["EMA"] = e9[-1] < e21[-1] < e50[-1]
    if info["EMA"]:
        s += 3

    slope_ok = e9[-1] < e9[-4] and e21[-1] < e21[-4]
    info["Slope"] = slope_ok
    if slope_ok:
        s += 1

    info["PB"] = detectar_pullback_short(cierres)
    if info["PB"]:
        s += 2

    r = rsi(cierres)
    info["RSI"] = r
    if 35 <= r <= 58:
        s += 2
    elif r < 28:
        s -= 2

    div_baj = divergencia_bajista(cierres)
    info["DivBaj"] = div_baj
    if div_baj:
        s += 2

    linea, senal, hist_act, hist_prev = macd_completo(cierres)
    info["MACD"] = linea < senal
    if linea < senal:
        s += 1
    info["MACDhist"] = hist_act < 0 and hist_act < hist_prev
    if hist_act < 0 and hist_act < hist_prev:
        s += 1

    vr = volumen_relativo(volumenes)
    info["Vol"] = vr
    if vr >= 1.3:
        s += 2
    elif vr >= 1.1:
        s += 1

    obv_vals = obv(cierres, volumenes)
    obv_baja = obv_vals[-1] < obv_vals[-5]
    info["OBV"] = obv_baja
    if obv_baja:
        s += 1

    bb_m, bb_sup, bb_inf = bollinger(cierres)
    if cierres[-1] < bb_m and cierres[-2] >= bb_m:
        s += 1
        info["BB"] = "cruce"
    elif cierres[-1] < bb_m:
        info["BB"] = "bajo"
    else:
        info["BB"] = "sobre"

    stk, std = stoch_rsi(cierres)
    info["StochRSI"] = stk
    if stk < std and 20 < stk < 80:
        s += 1

    info["Vela"] = patron_vela_bajista(cierres, altos, bajos, aperturas)
    if info["Vela"] :
        s += 1

    return s, info, r

# ================= MULTITF =================

def analizar_multitf(symbol):
    c1m, a1m, b1m, v1m, ap1m = get_klines(symbol, "1m", 60)
    c5m, a5m, b5m, v5m, ap5m = get_klines(symbol, "5m", 60)
    c15m, _, _, _, _          = get_klines(symbol, "15m", 60)

    e9_1m  = ema(c1m, 9)
    e21_1m = ema(c1m, 21)
    e9_5m  = ema(c5m, 9)
    e21_5m = ema(c5m, 21)
    e9_15m = ema(c15m, 9)
    e21_15m= ema(c15m, 21)

    long_1m  = e9_1m[-1]  > e21_1m[-1]
    long_5m  = e9_5m[-1]  > e21_5m[-1]
    long_15m = e9_15m[-1] > e21_15m[-1]

    short_1m  = e9_1m[-1]  < e21_1m[-1]
    short_5m  = e9_5m[-1]  < e21_5m[-1]
    short_15m = e9_15m[-1] < e21_15m[-1]

    bias_long  = long_1m and long_5m and long_15m
    bias_short = short_1m and short_5m and short_15m

    return bias_long, bias_short, c1m, a1m, b1m, v1m, ap1m, c15m

# ================= RESUMEN ESTADÍSTICO =================

def enviar_resumen():
    wr = (operaciones_ganadoras / operaciones_totales * 100) if operaciones_totales > 0 else 0
    msg = (
        f"📊 <b>RESUMEN HORARIO</b>\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
        f"📋 Operaciones: {operaciones_totales}\n"
        f"✅ Ganadoras: {operaciones_ganadoras}\n"
        f"❌ Perdedoras: {operaciones_totales - operaciones_ganadoras}\n"
        f"🎯 Win Rate: {wr:.1f}%\n"
        f"💵 PnL total: {pnl_total:+.4f}\n"
        f"📈 Racha actual: {'🔴 ' + str(racha_perdidas) + ' pérdidas' if racha_perdidas > 0 else '🟢 ' + str(racha_ganancias) + ' ganancias'}"
    )
    enviar_alerta(msg)

# ================= LOOP PRINCIPAL =================
while True:
    try:
        ahora = time.time()

        # ---- Resumen periódico ----
        if ahora - ultimo_resumen >= RESUMEN_CADA:
            enviar_resumen()
            ultimo_resumen = ahora

        # ================= GESTIÓN DE POSICIÓN ABIERTA =================
        if estado:
            cierres, altos, bajos, volumenes, aperturas = get_klines(symbol_activo, "1m", 30)
            precio = cierres[-1]
            atr_val = atr(altos, bajos, cierres)
            r_actual = rsi(cierres)

            if direccion == "long":
                ganancia    = precio - entrada
                ganancia_pct = (ganancia / entrada) * 100

                if precio > max_precio:
                    max_precio = precio

                sl_estructura = min(cierres[-5:])
                sl_atr        = entrada - 1.5 * atr_val
                sl_maximo     = entrada - 0.002 * entrada
                sl = max(sl_estructura, sl_atr, sl_maximo)

                riesgo = entrada - sl
                tp1 = entrada + riesgo * 1.5
                tp2 = entrada + riesgo * 2.5
                trailing_dist = (max_precio - entrada) * 0.45

                salir = None
                if precio <= sl:
                    salir = ("SL", "🛑")
                elif precio >= tp2:
                    salir = ("TP2", "💰")
                elif precio >= tp1 and r_actual > 75:
                    salir = ("TP1+RSI", "💰")
                elif ganancia > 0 and max_precio - precio >= trailing_dist:
                    salir = ("TRAILING", "💰")
                elif r_actual > 82:
                    salir = ("RSI-EXT", "⚡")

            else:  # short
                ganancia    = entrada - precio
                ganancia_pct = (ganancia / entrada) * 100

                if precio < min_precio:
                    min_precio = precio

                sl_estructura = max(cierres[-5:])
                sl_atr        = entrada + 1.5 * atr_val
                sl_maximo     = entrada + 0.002 * entrada
                sl = min(sl_estructura, sl_atr, sl_maximo)

                riesgo = sl - entrada
                tp1 = entrada - riesgo * 1.5
                tp2 = entrada - riesgo * 2.5
                trailing_dist = (entrada - min_precio) * 0.45

                salir = None
                if precio >= sl:
                    salir = ("SL", "🛑")
                elif precio <= tp2:
                    salir = ("TP2", "💰")
                elif precio <= tp1 and r_actual < 25:
                    salir = ("TP1+RSI", "💰")
                elif ganancia > 0 and precio - min_precio >= trailing_dist:
                    salir = ("TRAILING", "💰")
                elif r_actual < 18:
                    salir = ("RSI-EXT", "⚡")

            if salir:
                tipo_salida, emoji = salir
                es_ganadora = ganancia > 0

                operaciones_totales += 1
                pnl_total += ganancia

                if es_ganadora:
                    operaciones_ganadoras += 1
                    racha_ganancias += 1
                    racha_perdidas = 0
                    ganancia_acumulada += ganancia
                else:
                    racha_perdidas += 1
                    racha_ganancias = 0

                wr = (operaciones_ganadoras / operaciones_totales * 100)
                dir_emoji = "📈" if direccion == "long" else "📉"

                msg = (
                    f"{emoji} <b>{tipo_salida} — {symbol_activo}</b> {dir_emoji}\n"
                    f"Precio: {precio:.4f}\n"
                    f"PnL: {'+' if ganancia > 0 else ''}{ganancia:.4f} ({ganancia_pct:+.3f}%)\n"
                    f"RSI: {r_actual:.1f} | WR acum: {wr:.1f}%\n"
                    f"PnL total: {pnl_total:+.4f}"
                )
                enviar_alerta(msg)

                cooldowns[symbol_activo] = time.time()
                estado = False
                symbol_activo = None
                direccion = None

            time.sleep(5)
            continue

        # ================= PROTECCIONES =================
        if ganancia_acumulada >= 5:
            enviar_alerta("🛑 <b>PROTECCIÓN DE GANANCIA</b>\nPausa 2 min")
            time.sleep(120)
            ganancia_acumulada = 0
            continue

        if racha_perdidas >= 2:
            enviar_alerta(f"⛔ <b>PAUSA POR RACHA</b>\n{racha_perdidas} pérdidas seguidas")
            time.sleep(90)
            racha_perdidas = 0
            continue

        # ================= FILTRO DE SESIÓN =================
        if not sesion_activa():
            time.sleep(30)
            continue

        peso = peso_sesion()
        score_min_long  = SCORE_MIN_LONG  + (1 if peso < 0.8 else 0)
        score_min_short = SCORE_MIN_SHORT + (1 if peso < 0.8 else 0)

        # ================= FILTRO BTC MULTI-TF =================
        btc_long, btc_short, btc_1m, _, _, _, _, btc_15m = analizar_multitf("BTCUSDT")
        btc_rsi = rsi(btc_1m)
        regimen_btc = detectar_regimen(btc_15m)

        if regimen_btc == "LATERAL":
            time.sleep(10)
            continue

        mejor_long  = None
        mejor_short = None
        score_top_long  = 0
        score_top_short = 0

        # ================= SCAN =================
        for symbol in symbols:
            try:
                # Cooldown por símbolo
                if symbol in cooldowns and time.time() - cooldowns[symbol] < COOLDOWN_SYMBOL:
                    continue

                bias_long, bias_short, c1m, a1m, b1m, v1m, ap1m, c15m = analizar_multitf(symbol)

                precio = c1m[-1]
                atr_val = atr(a1m, b1m, c1m)

                if atr_val < precio * 0.0003:
                    continue

                # ---- LONG ----
                if btc_long and bias_long:
                    s, info, r = score_long(c1m, a1m, b1m, v1m, ap1m)
                    if s > score_top_long:
                        score_top_long = s
                        mejor_long = (symbol, precio, c1m, a1m, b1m, v1m, ap1m, info, r)

                # ---- SHORT ----
                if btc_short and bias_short:
                    s, info, r = score_short(c1m, a1m, b1m, v1m, ap1m)
                    if s > score_top_short:
                        score_top_short = s
                        mejor_short = (symbol, precio, c1m, a1m, b1m, v1m, ap1m, info, r)

            except Exception:
                continue

        # ================= ENTRADA LONG =================
        if mejor_long and score_top_long >= score_min_long:
            symbol_t, precio_t, c1m, a1m, b1m, v1m, ap1m, info, r = mejor_long

            atr_val = atr(a1m, b1m, c1m)
            sl_e  = min(c1m[-5:])
            sl_a  = precio_t - 1.5 * atr_val
            sl_mx = precio_t - 0.002 * precio_t
            sl    = max(sl_e, sl_a, sl_mx)
            riesgo = precio_t - sl

            if riesgo <= 0 or riesgo > 0.003 * precio_t:
                time.sleep(5)
                continue

            tp1 = precio_t + riesgo * 1.5
            tp2 = precio_t + riesgo * 2.5
            rr  = riesgo * 2.5 / riesgo
            tam = calcular_tamano(precio_t, sl)

            symbol_activo = symbol_t
            entrada       = precio_t
            max_precio    = entrada
            min_precio    = entrada
            estado        = True
            direccion     = "long"

            flags = []
            for k, v in info.items():
                if v is True:
                    flags.append(f"{k}✅")
                elif v is False:
                    flags.append(f"{k}❌")

            msg = (
                f"🚀 <b>LONG — {symbol_activo}</b>\n"
                f"💵 Entrada: {entrada:.4f}\n"
                f"🎯 Score: {score_top_long}/18\n"
                f"📉 SL: {sl:.4f}\n"
                f"🎯 TP1: {tp1:.4f}  TP2: {tp2:.4f}\n"
                f"📊 R:R = 1:{rr:.1f} | RSI: {r:.1f}\n"
                f"📦 Tamaño ref: {tam} unidades\n"
                f"🕐 Sesión: {peso*100:.0f}%\n"
                f"🔍 {' | '.join(flags[:6])}"
            )
            enviar_alerta(msg)

        # ================= ENTRADA SHORT =================
        elif mejor_short and score_top_short >= score_min_short:
            symbol_t, precio_t, c1m, a1m, b1m, v1m, ap1m, info, r = mejor_short

            atr_val = atr(a1m, b1m, c1m)
            sl_e  = max(c1m[-5:])
            sl_a  = precio_t + 1.5 * atr_val
            sl_mx = precio_t + 0.002 * precio_t
            sl    = min(sl_e, sl_a, sl_mx)
            riesgo = sl - precio_t

            if riesgo <= 0 or riesgo > 0.003 * precio_t:
                time.sleep(5)
                continue

            tp1 = precio_t - riesgo * 1.5
            tp2 = precio_t - riesgo * 2.5
            rr  = riesgo * 2.5 / riesgo
            tam = calcular_tamano(precio_t, sl)

            symbol_activo = symbol_t
            entrada       = precio_t
            min_precio    = entrada
            max_precio    = entrada
            estado        = True
            direccion     = "short"

            flags = []
            for k, v in info.items():
                if v is True:
                    flags.append(f"{k}✅")
                elif v is False:
                    flags.append(f"{k}❌")

            msg = (
                f"📉 <b>SHORT — {symbol_activo}</b>\n"
                f"💵 Entrada: {entrada:.4f}\n"
                f"🎯 Score: {score_top_short}/18\n"
                f"📈 SL: {sl:.4f}\n"
                f"🎯 TP1: {tp1:.4f}  TP2: {tp2:.4f}\n"
                f"📊 R:R = 1:{rr:.1f} | RSI: {r:.1f}\n"
                f"📦 Tamaño ref: {tam} unidades\n"
                f"🕐 Sesión: {peso*100:.0f}%\n"
                f"🔍 {' | '.join(flags[:6])}"
            )
            enviar_alerta(msg)

        time.sleep(5)

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
        time.sleep(5)
