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
ultimo_trade = 0

racha_perdidas = 0
ganancia_acumulada = 0

enviar_alerta("🔥 BOT MULTI-MERCADO PRO ACTIVO")

def obtener_score(cierres, precio):
    score = 0

    # tendencia
    media_corta = sum(cierres[-5:]) / 5
    media_larga = sum(cierres[-15:]) / 15

    if media_corta > media_larga:
        score += 2

    # momentum
    if cierres[-1] > cierres[-2] > cierres[-3]:
        score += 2

    if (cierres[-1] - cierres[-5]) > (0.0007 * precio):
        score += 2

    # fuerza
    if (cierres[-1] - cierres[-2]) > (0.0004 * precio):
        score += 1

    # evitar pico
    subida = (cierres[-1] - cierres[-6]) / precio
    if subida < 0.003:
        score += 1

    return score

while True:
    try:

        if estado:
            # ================= GESTIÓN =================
            data = requests.get(
                f"https://api.binance.com/api/v3/klines?symbol={symbol_activo}&interval=1m&limit=10"
            ).json()

            cierres = [float(x[4]) for x in data]
            precio = cierres[-1]

            ganancia = precio - entrada

            if precio > max_precio:
                max_precio = precio

            tp = 0.004 * precio
            sl = 0.0025 * precio
            trailing = 0.0018 * precio

            if max_precio - precio >= trailing and ganancia > 0:
                enviar_alerta(f"💰 TRAILING {symbol_activo}\n{precio}\n+{ganancia:.4f}")
                estado = False
                racha_perdidas = 0
                ganancia_acumulada += ganancia
                time.sleep(20)

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
        if ganancia_acumulada >= 2:
            enviar_alerta("🛑 PROTECCIÓN ACTIVADA")
            time.sleep(120)
            ganancia_acumulada = 0
            continue

        if racha_perdidas >= 2:
            enviar_alerta("⛔ PAUSA POR RACHAS")
            time.sleep(60)
            racha_perdidas = 0
            continue

        mejor_score = 0
        mejor_symbol = None
        mejor_precio = 0

        # ================= ANALIZAR TODOS =================
        for symbol in symbols:
            data = requests.get(
                f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=30"
            ).json()

            cierres = [float(x[4]) for x in data]
            precio = cierres[-1]

            rango = max(cierres[-10:]) - min(cierres[-10:])
            if rango < (0.0015 * precio):
                continue

            score = obtener_score(cierres, precio)

            if score > mejor_score:
                mejor_score = score
                mejor_symbol = symbol
                mejor_precio = precio

        # ================= ENTRAR SOLO SI ES MUY BUENO =================
        if mejor_score >= 6:
            estado = True
            entrada = mejor_precio
            max_precio = mejor_precio
            symbol_activo = mejor_symbol
            ultimo_trade = time.time()

            enviar_alerta(f"🚀 ENTRADA {symbol_activo}\n{entrada}\nScore: {mejor_score}")

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
