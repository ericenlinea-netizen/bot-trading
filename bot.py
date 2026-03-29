import requests
import time

# ================= TELEGRAM =================
TOKEN = "8772294732:AAGU62SChVJfmwf9RpweG-inBGAjIDlMwms"
CHAT_ID = "5019372975"

def enviar_alerta(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass

# ================= CONFIG =================
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

estado = False
entrada = 0
max_precio = 0
symbol_activo = None

racha_perdidas = 0
ganancia_acumulada = 0

enviar_alerta("🏦 BOT INSTITUCIONAL ACTIVO")

# ================= FUNCIONES =================
def get_cierres(symbol, interval, limit=30):
    data = requests.get(
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    ).json()
    return [float(x[4]) for x in data]

def tendencia(cierres):
    return (sum(cierres[-5:]) / 5) > (sum(cierres[-15:]) / 15)

def score_market(cierres, precio):
    score = 0

    # tendencia
    if tendencia(cierres):
        score += 2

    # momentum limpio
    if cierres[-1] > cierres[-2] > cierres[-3]:
        score += 2

    # impulso fuerte
    if (cierres[-1] - cierres[-5]) > (0.0008 * precio):
        score += 2

    # fuerza vela actual
    if (cierres[-1] - cierres[-2]) > (0.0004 * precio):
        score += 1

    # evitar pico
    subida = (cierres[-1] - cierres[-6]) / precio
    if subida < 0.0025:
        score += 1

    return score

# ================= LOOP =================
while True:
    try:

        # ================= GESTIÓN =================
        if estado:
            cierres = get_cierres(symbol_activo, "1m", 10)
            precio = cierres[-1]

            ganancia = precio - entrada

            if precio > max_precio:
                max_precio = precio

            tp = 0.004 * precio
            sl = 0.0025 * precio
            trailing = 0.0015 * precio

            if max_precio - precio >= trailing and ganancia > 0:
                enviar_alerta(f"💰 TRAILING {symbol_activo}\n{precio}\n+{ganancia:.4f}")
                estado = False
                racha_perdidas = 0
                ganancia_acumulada += ganancia
                time.sleep(15)

            elif ganancia >= tp:
                enviar_alerta(f"💰 TP {symbol_activo}\n{precio}\n+{ganancia:.4f}")
                estado = False
                racha_perdidas = 0
                ganancia_acumulada += ganancia
                time.sleep(20)

            elif ganancia <= -sl:
                enviar_alerta(f"🛑 SL {symbol_activo}\n{precio}\n{ganancia:.4f}")
                estado = False
                racha_perdidas += 1

            time.sleep(5)
            continue

        # ================= PROTECCIÓN =================
        if ganancia_acumulada >= 3:
            enviar_alerta("🛑 PROTECCIÓN DE GANANCIA")
            time.sleep(120)
            ganancia_acumulada = 0
            continue

        if racha_perdidas >= 2:
            enviar_alerta("⛔ PAUSA POR RACHAS")
            time.sleep(90)
            racha_perdidas = 0
            continue

        # ================= FILTRO GLOBAL BTC =================
        btc_1m = get_cierres("BTCUSDT", "1m", 20)
        btc_5m = get_cierres("BTCUSDT", "5m", 20)

        if not (tendencia(btc_1m) and tendencia(btc_5m)):
            time.sleep(5)
            continue

        mejor_score = 0
        mejor_symbol = None
        mejor_precio = 0

        # ================= SCAN =================
        for symbol in symbols:

            cierres_1m = get_cierres(symbol, "1m", 30)
            cierres_5m = get_cierres(symbol, "5m", 30)

            precio = cierres_1m[-1]

            # evitar rango muerto
            rango = max(cierres_1m[-10:]) - min(cierres_1m[-10:])
            if rango < (0.0015 * precio):
                continue

            # confirmación multi timeframe
            if not (tendencia(cierres_1m) and tendencia(cierres_5m)):
                continue

            # evitar entrada tardía
            retroceso = (precio - max(cierres_1m[-5:])) / precio
            if retroceso < -0.0008:
                continue

            score = score_market(cierres_1m, precio)

            if score > mejor_score:
                mejor_score = score
                mejor_symbol = symbol
                mejor_precio = precio

        # ================= ENTRADA ULTRA FILTRADA =================
        if mejor_score >= 7:
            estado = True
            entrada = mejor_precio
            max_precio = mejor_precio
            symbol_activo = mejor_symbol

            enviar_alerta(
                f"🚀 ENTRADA {symbol_activo}\n{entrada}\nScore: {mejor_score}"
            )

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
