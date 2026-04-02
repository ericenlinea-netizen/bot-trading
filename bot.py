import requests
import time
import math
from datetime import datetime, timezone

# ================= TELEGRAM =================
TOKEN = "8750698916:AAEgYA-AQqienTfKYd8GzGTBj7ypjrPz_UM"
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

# ============================================================
# CONFIG GENERAL
# ------------------------------------------------------------
# Filosofía: Swing sobre 5m/15m. Menos operaciones, más calidad.
# Cada entrada debe justificar costos reales de Binance (~0.1%
# por lado = 0.2% ida y vuelta). Se exige mínimo 0.5% de margen
# sobre el TP1 para que tenga sentido operar.
# ============================================================

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
           "ADAUSDT", "XRPUSDT", "DOGEUSDT", "LINKUSDT"]

CAPITAL_BASE      = 100.0    # USDT de referencia para sizing
RIESGO_PCT        = 0.01     # 1% del capital por operación
FEE_ROUND_TRIP    = 0.002    # 0.2% = 0.1% entrada + 0.1% salida
MIN_PROFIT_PCT    = 0.005    # TP1 debe ser al menos 0.5% sobre entrada
MIN_RR            = 2.0      # R:R mínimo aceptable (tp/sl)
SCORE_MIN         = 11       # Score mínimo sobre 18 puntos posibles
MAX_ATR_PCT       = 0.015    # No entrar si ATR > 1.5% (demasiado riesgo)
MIN_ATR_PCT       = 0.003    # No entrar si ATR < 0.3% (sin movimiento)
COOLDOWN_SYMBOL   = 600      # 10 min entre operaciones del mismo símbolo
RESUMEN_CADA      = 3600     # Resumen estadístico cada hora

# Estado de posición
estado     = False
direccion  = None
entrada    = 0.0
max_precio = 0.0
min_precio = float("inf")
symbol_act = None

# Estadísticas
racha_perdidas   = 0
racha_ganancias  = 0
gan_acumulada    = 0.0
ops_total        = 0
ops_ganadoras    = 0
pnl_total        = 0.0
cooldowns        = {}
ultimo_resumen   = time.time()

enviar_alerta(
    "📊 <b>BOT SWING v4 ACTIVO</b>\n"
    f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
    f"📐 TF primario: 5m | Confirmación: 15m + 1h\n"
    f"🎯 Score mínimo: {SCORE_MIN}/18 | Fee: {FEE_ROUND_TRIP*100:.1f}% RT\n"
    f"💵 Capital ref: ${CAPITAL_BASE} | Riesgo: {RIESGO_PCT*100:.1f}%"
)

# ================= OBTENCIÓN DE DATOS =================

def get_klines(symbol, interval, limit=100):
    url = (f"https://api.binance.com/api/v3/klines"
           f"?symbol={symbol}&interval={interval}&limit={limit}")
    data = requests.get(url, timeout=10).json()
    c = [float(x[4]) for x in data]   # close
    h = [float(x[2]) for x in data]   # high
    l = [float(x[3]) for x in data]   # low
    v = [float(x[5]) for x in data]   # volume
    o = [float(x[1]) for x in data]   # open
    return c, h, l, v, o

# ================= INDICADORES =================

def ema(vals, n):
    k = 2 / (n + 1)
    e = [vals[0]]
    for v in vals[1:]:
        e.append(v * k + e[-1] * (1 - k))
    return e

def rsi(c, n=14):
    g, p = [], []
    for i in range(1, len(c)):
        d = c[i] - c[i-1]
        g.append(max(d, 0))
        p.append(max(-d, 0))
    if len(g) < n:
        return 50.0
    ag = sum(g[-n:]) / n
    ap = sum(p[-n:]) / n
    return 100.0 if ap == 0 else 100 - 100 / (1 + ag / ap)

def macd(c):
    e12 = ema(c, 12)
    e26 = ema(c, 26)
    lin = [a - b for a, b in zip(e12, e26)]
    sig = ema(lin, 9)
    hist = [l - s for l, s in zip(lin, sig)]
    return lin[-1], sig[-1], hist[-1], hist[-2] if len(hist) > 1 else 0

def atr(h, l, c, n=14):
    trs = [max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
           for i in range(1, len(c))]
    if len(trs) < n:
        return c[-1] * 0.005
    return sum(trs[-n:]) / n

def bollinger(c, n=20, k=2.0):
    if len(c) < n:
        return c[-1], c[-1]*1.02, c[-1]*0.98
    w = c[-n:]
    m = sum(w) / n
    s = math.sqrt(sum((x-m)**2 for x in w) / n)
    return m, m + k*s, m - k*s

def stoch_rsi(c, rsi_n=14, stoch_n=14, smooth=3):
    rsis = []
    for i in range(rsi_n, len(c)):
        rsis.append(rsi(c[:i+1], rsi_n))
    if len(rsis) < stoch_n:
        return 50.0, 50.0
    w = rsis[-stoch_n:]
    mn, mx = min(w), max(w)
    if mx == mn:
        return 50.0, 50.0
    k_val = (rsis[-1] - mn) / (mx - mn) * 100
    d_val = sum(((rsis[-i] - mn) / (mx - mn)) * 100
                for i in range(1, min(smooth+1, len(rsis)+1))) / smooth
    return k_val, d_val

def obv(c, v):
    o = [0.0]
    for i in range(1, len(c)):
        o.append(o[-1] + (v[i] if c[i] > c[i-1] else
                          -v[i] if c[i] < c[i-1] else 0))
    return o

def vol_relativo(v, n=20):
    if len(v) < n:
        return 1.0
    avg = sum(v[-n:-1]) / (n-1)
    return v[-1] / avg if avg > 0 else 1.0

def divergencia_alcista(c, n=14):
    if len(c) < 35:
        return False
    r_now  = rsi(c, n)
    r_prev = rsi(c[:-6], n)
    return c[-1] < c[-7] and r_now > r_prev + 3

def divergencia_bajista(c, n=14):
    if len(c) < 35:
        return False
    r_now  = rsi(c, n)
    r_prev = rsi(c[:-6], n)
    return c[-1] > c[-7] and r_now < r_prev - 3

# ================= FILTRO DE VIABILIDAD =================

def viabilidad_entry(precio, sl, atr_val, direccion):
    """
    Verifica que la operación cubra fees y tenga movimiento suficiente.
    Retorna (ok, motivo).
    """
    riesgo = abs(precio - sl)

    # --- Riesgo mínimo: cubrir fees más margen ---
    min_riesgo = precio * (FEE_ROUND_TRIP + MIN_PROFIT_PCT / MIN_RR)
    if riesgo < min_riesgo:
        return False, f"Riesgo {riesgo/precio*100:.3f}% < mínimo {min_riesgo/precio*100:.3f}%"

    # --- Riesgo máximo: no sobredimensionar ---
    if riesgo > precio * 0.015:
        return False, f"Riesgo excesivo {riesgo/precio*100:.2f}%"

    # --- ATR en rango aceptable ---
    atr_pct = atr_val / precio
    if atr_pct < MIN_ATR_PCT:
        return False, f"ATR {atr_pct*100:.3f}% muy bajo (sin movimiento)"
    if atr_pct > MAX_ATR_PCT:
        return False, f"ATR {atr_pct*100:.3f}% muy alto (riesgo extremo)"

    # --- TP1 cubre fees con margen ---
    tp1_dist = riesgo * MIN_RR
    tp1_pct  = tp1_dist / precio
    if tp1_pct < FEE_ROUND_TRIP + MIN_PROFIT_PCT:
        return False, f"TP1 {tp1_pct*100:.3f}% no cubre fees+profit mínimo"

    return True, "OK"

# ================= SESIÓN HORARIA =================

def hora_utc():
    return datetime.now(timezone.utc).hour

def sesion_activa():
    h = hora_utc()
    # Cierre entre 22-00 UTC: volumen bajo, spread alto
    return not (22 <= h or h < 1)

def peso_sesion():
    h = hora_utc()
    if 13 <= h < 21:  return 1.0   # Solapamiento EU+US
    if  7 <= h < 16:  return 0.85  # Europa
    if  1 <= h <  8:  return 0.75  # Asia
    return 0.6

# ================= SIZING =================

def calcular_tamano(precio, sl):
    distancia = abs(precio - sl)
    if distancia == 0:
        return 0.0
    riesgo_usd = CAPITAL_BASE * RIESGO_PCT
    return round(riesgo_usd / distancia, 6)

# ================= SCORES =================

def _ema_alineado_long(c):
    e9, e21, e50 = ema(c, 9), ema(c, 21), ema(c, 50)
    return e9[-1] > e21[-1] > e50[-1], e9, e21, e50

def _ema_alineado_short(c):
    e9, e21, e50 = ema(c, 9), ema(c, 21), ema(c, 50)
    return e9[-1] < e21[-1] < e50[-1], e9, e21, e50

def pullback_long(c, e9):
    """Retroceso hasta zona EMA9 y recuperación."""
    subida    = c[-7] < c[-6] < c[-5]
    retro     = c[-5] > c[-4] and c[-4] <= c[-3]
    recupera  = c[-1] > c[-2] > c[-3]
    soporte   = c[-1] >= e9[-1] * 0.998
    return subida and retro and recupera and soporte

def pullback_short(c, e9):
    bajada    = c[-7] > c[-6] > c[-5]
    rebote    = c[-5] < c[-4] and c[-4] >= c[-3]
    retoma    = c[-1] < c[-2] < c[-3]
    resist    = c[-1] <= e9[-1] * 1.002
    return bajada and rebote and retoma and resist

def vela_alcista_fuerte(c, h, l, o):
    """Marubozu o martillo alcista con cuerpo > 50% del rango."""
    cuerpo = c[-1] - o[-1]
    rango  = h[-1] - l[-1]
    if rango < 1e-9:
        return False
    mecha_inf = (min(o[-1], c[-1]) - l[-1]) / rango
    return c[-1] > o[-1] and cuerpo / rango > 0.5 and mecha_inf > 0.2

def vela_bajista_fuerte(c, h, l, o):
    cuerpo = o[-1] - c[-1]
    rango  = h[-1] - l[-1]
    if rango < 1e-9:
        return False
    mecha_sup = (h[-1] - max(o[-1], c[-1])) / rango
    return c[-1] < o[-1] and cuerpo / rango > 0.5 and mecha_sup > 0.2

def score_long(c5, h5, l5, v5, o5, c15, c1h):
    """Score sobre 18 puntos usando 5m como primario."""
    s = 0
    flags = {}

    alin, e9, e21, e50 = _ema_alineado_long(c5)
    flags["EMA-alin"] = alin
    if alin:
        s += 3

    # Pendiente EMA positiva en 15m
    e21_15 = ema(c15, 21)
    slope15 = e21_15[-1] > e21_15[-5]
    flags["Slope15"] = slope15
    if slope15:
        s += 1

    # 1h también alcista
    e21_1h = ema(c1h, 21)
    long_1h = c1h[-1] > e21_1h[-1]
    flags["1h-alcista"] = long_1h
    if long_1h:
        s += 1

    # Pullback hasta EMA9 y recuperación
    pb = pullback_long(c5, e9)
    flags["Pullback"] = pb
    if pb:
        s += 2

    # RSI zona momentum sin sobrecompra
    r5 = rsi(c5)
    flags["RSI5m"] = round(r5, 1)
    if 45 <= r5 <= 65:
        s += 2
    elif r5 > 70:
        s -= 2
    elif r5 < 40:
        s -= 1

    # Divergencia alcista 5m
    div = divergencia_alcista(c5)
    flags["DivAlc"] = div
    if div:
        s += 2

    # MACD 5m positivo y acelerando
    lin5, sig5, hist5, hist5p = macd(c5)
    flags["MACD"] = lin5 > sig5
    if lin5 > sig5:
        s += 1
    if hist5 > 0 and hist5 > hist5p:
        flags["MACDacel"] = True
        s += 1
    else:
        flags["MACDacel"] = False

    # Volumen: al menos 1.5x el promedio
    vr = vol_relativo(v5)
    flags["Vol"] = round(vr, 2)
    if vr >= 1.5:
        s += 2
    elif vr >= 1.2:
        s += 1
    elif vr < 0.8:
        s -= 1

    # OBV ascendente
    obv_vals = obv(c5, v5)
    obv_ok = obv_vals[-1] > obv_vals[-6]
    flags["OBV"] = obv_ok
    if obv_ok:
        s += 1

    # Vela de fuerza alcista en 5m
    vela = vela_alcista_fuerte(c5, h5, l5, o5)
    flags["Vela"] = vela
    if vela:
        s += 1

    # Stoch RSI cruzando al alza
    stk, std = stoch_rsi(c5)
    flags["StochRSI"] = round(stk, 1)
    if stk > std and 20 < stk < 75:
        s += 1

    return max(s, 0), flags, r5

def score_short(c5, h5, l5, v5, o5, c15, c1h):
    s = 0
    flags = {}

    alin, e9, e21, e50 = _ema_alineado_short(c5)
    flags["EMA-alin"] = alin
    if alin:
        s += 3

    e21_15 = ema(c15, 21)
    slope15 = e21_15[-1] < e21_15[-5]
    flags["Slope15"] = slope15
    if slope15:
        s += 1

    e21_1h = ema(c1h, 21)
    short_1h = c1h[-1] < e21_1h[-1]
    flags["1h-bajista"] = short_1h
    if short_1h:
        s += 1

    pb = pullback_short(c5, e9)
    flags["Pullback"] = pb
    if pb:
        s += 2

    r5 = rsi(c5)
    flags["RSI5m"] = round(r5, 1)
    if 35 <= r5 <= 55:
        s += 2
    elif r5 < 30:
        s -= 2
    elif r5 > 60:
        s -= 1

    div = divergencia_bajista(c5)
    flags["DivBaj"] = div
    if div:
        s += 2

    lin5, sig5, hist5, hist5p = macd(c5)
    flags["MACD"] = lin5 < sig5
    if lin5 < sig5:
        s += 1
    if hist5 < 0 and hist5 < hist5p:
        flags["MACDacel"] = True
        s += 1
    else:
        flags["MACDacel"] = False

    vr = vol_relativo(v5)
    flags["Vol"] = round(vr, 2)
    if vr >= 1.5:
        s += 2
    elif vr >= 1.2:
        s += 1
    elif vr < 0.8:
        s -= 1

    obv_vals = obv(c5, v5)
    obv_ok = obv_vals[-1] < obv_vals[-6]
    flags["OBV"] = obv_ok
    if obv_ok:
        s += 1

    vela = vela_bajista_fuerte(c5, h5, l5, o5)
    flags["Vela"] = vela
    if vela:
        s += 1

    stk, std = stoch_rsi(c5)
    flags["StochRSI"] = round(stk, 1)
    if stk < std and 25 < stk < 80:
        s += 1

    return max(s, 0), flags, r5

# ================= FILTRO BTC =================

def contexto_btc():
    """Retorna si BTC tiene tendencia clara (long/short/neutral) en 5m y 1h."""
    c5, _, _, _, _  = get_klines("BTCUSDT", "5m", 60)
    c1h, _, _, _, _ = get_klines("BTCUSDT", "1h", 60)

    e9_5  = ema(c5, 9)
    e21_5 = ema(c5, 21)
    e9_1h  = ema(c1h, 9)
    e21_1h = ema(c1h, 21)

    btc_long  = e9_5[-1] > e21_5[-1] and e9_1h[-1] > e21_1h[-1]
    btc_short = e9_5[-1] < e21_5[-1] and e9_1h[-1] < e21_1h[-1]
    btc_rsi5  = rsi(c5)

    # Mercado lateral si EMAs muy juntas
    diff = abs(e9_5[-1] - e21_5[-1]) / e21_5[-1]
    btc_lateral = diff < 0.001

    return btc_long, btc_short, btc_lateral, btc_rsi5

# ================= RESUMEN =================

def enviar_resumen():
    wr = (ops_ganadoras / ops_total * 100) if ops_total > 0 else 0.0
    enviar_alerta(
        f"📊 <b>RESUMEN HORARIO</b>\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
        f"📋 Ops: {ops_total} | ✅ {ops_ganadoras} | ❌ {ops_total - ops_ganadoras}\n"
        f"🎯 Win Rate: {wr:.1f}%\n"
        f"💵 PnL total: {pnl_total:+.6f}\n"
        f"{'🟢 Racha +' + str(racha_ganancias) if racha_ganancias else '🔴 Racha -' + str(racha_perdidas)}"
    )

# ================= LOOP PRINCIPAL =================

while True:
    try:
        ahora = time.time()

        # Resumen periódico
        if ahora - ultimo_resumen >= RESUMEN_CADA:
            enviar_resumen()
            ultimo_resumen = ahora

        # ===== GESTIÓN DE POSICIÓN ABIERTA =====
        if estado:
            c5, h5, l5, v5, o5 = get_klines(symbol_act, "5m", 30)
            precio   = c5[-1]
            atr_val  = atr(h5, l5, c5)
            r_actual = rsi(c5)

            if direccion == "long":
                gan = precio - entrada
                gan_pct = gan / entrada * 100
                if precio > max_precio:
                    max_precio = precio

                sl_e  = min(l5[-6:])
                sl_a  = entrada - 1.5 * atr_val
                sl_mx = entrada - 0.015 * entrada
                sl    = max(sl_e, sl_a, sl_mx)

                riesgo = entrada - sl
                tp1 = entrada + riesgo * MIN_RR
                tp2 = entrada + riesgo * 3.0
                trail_dist = (max_precio - entrada) * 0.45

                salir = None
                if precio <= sl:
                    salir = ("SL", "🛑")
                elif precio >= tp2:
                    salir = ("TP2", "💰💰")
                elif precio >= tp1 and r_actual > 73:
                    salir = ("TP1+RSI", "💰")
                elif gan > 0 and (max_precio - precio) >= trail_dist:
                    salir = ("TRAILING", "💰")
                elif r_actual > 82:
                    salir = ("RSI-EXTREME", "⚡")

            else:  # short
                gan = entrada - precio
                gan_pct = gan / entrada * 100
                if precio < min_precio:
                    min_precio = precio

                sl_e  = max(h5[-6:])
                sl_a  = entrada + 1.5 * atr_val
                sl_mx = entrada + 0.015 * entrada
                sl    = min(sl_e, sl_a, sl_mx)

                riesgo = sl - entrada
                tp1 = entrada - riesgo * MIN_RR
                tp2 = entrada - riesgo * 3.0
                trail_dist = (entrada - min_precio) * 0.45

                salir = None
                if precio >= sl:
                    salir = ("SL", "🛑")
                elif precio <= tp2:
                    salir = ("TP2", "💰💰")
                elif precio <= tp1 and r_actual < 27:
                    salir = ("TP1+RSI", "💰")
                elif gan > 0 and (precio - min_precio) >= trail_dist:
                    salir = ("TRAILING", "💰")
                elif r_actual < 18:
                    salir = ("RSI-EXTREME", "⚡")

            if salir:
                tipo, emoji = salir
                es_win = gan > 0
                ops_total    += 1
                pnl_total    += gan

                if es_win:
                    ops_ganadoras  += 1
                    racha_ganancias += 1
                    racha_perdidas  = 0
                    gan_acumulada  += gan
                else:
                    racha_perdidas  += 1
                    racha_ganancias = 0

                wr = ops_ganadoras / ops_total * 100
                dir_e = "📈" if direccion == "long" else "📉"
                enviar_alerta(
                    f"{emoji} <b>{tipo} — {symbol_act}</b> {dir_e}\n"
                    f"Precio: {precio:.5f}\n"
                    f"PnL: {gan:+.5f} ({gan_pct:+.3f}%)\n"
                    f"RSI: {r_actual:.1f} | WR: {wr:.1f}%\n"
                    f"PnL acum: {pnl_total:+.5f}"
                )

                cooldowns[symbol_act] = time.time()
                estado    = False
                symbol_act = None
                direccion  = None

            time.sleep(15)
            continue

        # ===== PROTECCIONES =====
        if gan_acumulada >= 3:
            enviar_alerta("🛑 <b>PROTECCIÓN DE GANANCIA</b>\nPausa 3 min")
            time.sleep(180)
            gan_acumulada = 0
            continue

        if racha_perdidas >= 2:
            enviar_alerta(f"⛔ <b>PAUSA POR RACHA NEGATIVA</b>\n{racha_perdidas} ops perdidas seguidas")
            time.sleep(120)
            racha_perdidas = 0
            continue

        # ===== FILTRO DE SESIÓN =====
        if not sesion_activa():
            time.sleep(60)
            continue

        peso = peso_sesion()
        score_req = SCORE_MIN + (1 if peso < 0.8 else 0)

        # ===== CONTEXTO BTC =====
        btc_long, btc_short, btc_lateral, btc_rsi5 = contexto_btc()

        if btc_lateral:
            time.sleep(20)
            continue

        if btc_rsi5 > 82 and btc_long:
            # BTC sobrecomprado — evitar longs nuevos
            btc_long = False

        if btc_rsi5 < 18 and btc_short:
            # BTC sobrevendido — evitar shorts nuevos
            btc_short = False

        mejor_long  = None
        mejor_short = None
        top_long    = 0
        top_short   = 0

        # ===== SCAN DE MERCADO =====
        for symbol in SYMBOLS:
            try:
                if symbol in cooldowns and time.time() - cooldowns[symbol] < COOLDOWN_SYMBOL:
                    continue

                c5,  h5,  l5,  v5,  o5  = get_klines(symbol, "5m",  80)
                c15, h15, l15, v15, o15 = get_klines(symbol, "15m", 60)
                c1h, h1h, l1h, v1h, o1h = get_klines(symbol, "1h",  60)

                precio   = c5[-1]
                atr_val  = atr(h5, l5, c5)

                # Filtro ATR absoluto
                atr_pct = atr_val / precio
                if atr_pct < MIN_ATR_PCT or atr_pct > MAX_ATR_PCT:
                    continue

                # --- LONG ---
                if btc_long:
                    sl_e  = min(l5[-6:])
                    sl_a  = precio - 1.5 * atr_val
                    sl_mx = precio - 0.012 * precio
                    sl    = max(sl_e, sl_a, sl_mx)

                    ok, motivo = viabilidad_entry(precio, sl, atr_val, "long")
                    if ok:
                        s, flags, r = score_long(c5, h5, l5, v5, o5, c15, c1h)
                        if s >= score_req and s > top_long:
                            top_long   = s
                            mejor_long = (symbol, precio, c5, h5, l5, v5, o5, flags, r, sl)

                # --- SHORT ---
                if btc_short:
                    sl_e  = max(h5[-6:])
                    sl_a  = precio + 1.5 * atr_val
                    sl_mx = precio + 0.012 * precio
                    sl    = min(sl_e, sl_a, sl_mx)

                    ok, motivo = viabilidad_entry(precio, sl, atr_val, "short")
                    if ok:
                        s, flags, r = score_short(c5, h5, l5, v5, o5, c15, c1h)
                        if s >= score_req and s > top_short:
                            top_short   = s
                            mejor_short = (symbol, precio, c5, h5, l5, v5, o5, flags, r, sl)

            except Exception:
                continue

        # ===== ENTRADA LONG =====
        def abrir_posicion(sym, precio, c5, h5, l5, v5, o5, flags, r, sl, direc):
            global estado, direccion, entrada, max_precio, min_precio, symbol_act

            atr_val = atr(h5, l5, c5)
            riesgo  = abs(precio - sl)
            tp1     = precio + riesgo * MIN_RR  if direc == "long" else precio - riesgo * MIN_RR
            tp2     = precio + riesgo * 3.0     if direc == "long" else precio - riesgo * 3.0
            rr_str  = f"1:{MIN_RR:.1f} → 1:3.0"
            tam     = calcular_tamano(precio, sl)
            dir_e   = "📈" if direc == "long" else "📉"
            sl_lbl  = "SL" if direc == "long" else "SL"

            flag_list = []
            for k, v in flags.items():
                if v is True:
                    flag_list.append(f"{k}✅")
                elif v is False:
                    flag_list.append(f"{k}❌")
                elif isinstance(v, (int, float)):
                    flag_list.append(f"{k}:{v}")

            symbol_act = sym
            entrada    = precio
            max_precio = precio
            min_precio = precio
            estado     = True
            direccion  = direc

            score_val = top_long if direc == "long" else top_short
            enviar_alerta(
                f"{'🚀' if direc == 'long' else '🔻'} <b>{'LONG' if direc == 'long' else 'SHORT'} — {sym}</b> {dir_e}\n"
                f"💵 Entrada: {precio:.5f}\n"
                f"🎯 Score: {score_val}/18 (req {score_req})\n"
                f"📉 {sl_lbl}: {sl:.5f}  ({abs(precio-sl)/precio*100:.3f}%)\n"
                f"🎯 TP1: {tp1:.5f} | TP2: {tp2:.5f}\n"
                f"📊 R:R {rr_str} | RSI: {r:.1f}\n"
                f"📦 Tamaño ref: {tam} u | Sesión: {peso*100:.0f}%\n"
                f"🔍 {' '.join(flag_list[:7])}"
            )

        if mejor_long:
            sym, precio, c5, h5, l5, v5, o5, flags, r, sl = mejor_long
            abrir_posicion(sym, precio, c5, h5, l5, v5, o5, flags, r, sl, "long")

        elif mejor_short:
            sym, precio, c5, h5, l5, v5, o5, flags, r, sl = mejor_short
            abrir_posicion(sym, precio, c5, h5, l5, v5, o5, flags, r, sl, "short")

        time.sleep(20)

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
        time.sleep(10)
