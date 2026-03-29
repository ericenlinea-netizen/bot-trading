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

enviar_alerta("🏦 HEDGE BOT ACTIVADO")

# ================= FUNCIONES =================
def get_cierres(symbol, interval, limit=30):
    data = requests.get(
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    ).json()
    return [float(x[4]) for x in data]

def tendencia(cierres):
    return (sum(cierres[-5:]) / 5) > (sum(cierres[-15:]) / 15)

def detectar_pullback(cierres):
    # tendencia previa
    subida = cierres[-4] < cierres[-3] < cierres[-2]

    # retroceso
    retroceso = cierres[-2] > cierres[-1]

    # rebote
    rebote = cierres[-1] > cierres[-2]

    return subida and rebote

def fuerza(cierres, precio):
    return (cierres[-1] - cierres[-2]) > (0.0004 * precio)

def score(cierres, precio):
    s = 0

    if tendencia(cierres):
        s += 2

    if fuerza(cierres, precio):
        s += 2

    if (cierres[-1] - cierres[-5]) > (0.0008 * precio):
        s += 2

    subida = (cierres[-1] - cierres[-6]) / precio
    if subida < 0.0025:
        s += 1

    return s

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

            # SL estructural
            sl = min(cierres[-5:])

            # TP dinámico
            tp = entrada + (entrada - sl) * 2

            trailing = (max_precio - entrada) * 0.5

            if precio <= sl:
                enviar_alerta(f"🛑 SL {symbol_activo}\n{precio}\n{ganancia:.4f}")
                estado = False
                racha_perdidas += 1

            elif precio >= tp:
                enviar_alerta(f"💰 TP {symbol_activo}\n{precio}\n+{ganancia:.4f}")
                estado = False
                racha_perdidas = 0
                ganancia_acumulada += ganancia

            elif max_precio - precio >= trailing and ganancia > 0:
                enviar_alerta(f"💰 TRAILING {symbol_activo}\n{precio}\n+{ganancia:.4f}")
                estado = False
                racha_perdidas = 0
                ganancia_acumulada += ganancia

            time.sleep(5)
            continue

        # ================= PROTECCIÓN =================
        if ganancia_acumulada >= 5:
            enviar_alerta("🛑 PROTECCIÓN DE GANANCIA")
            time.sleep(120)
            ganancia_acumulada = 0
            continue

        if racha_perdidas >= 2:
            enviar_alerta("⛔ PAUSA POR RACHAS")
            time.sleep(90)
            racha_perdidas = 0
            continue

        # ================= FILTRO BTC =================
        btc_1m = get_cierres("BTCUSDT", "1m", 20)
        btc_5m = get_cierres("BTCUSDT", "5m", 20)

        if not (tendencia(btc_1m) and tendencia(btc_5m)):
            time.sleep(5)
            continue

        mejor = None
        mejor_score = 0

        # ================= SCAN =================
        for symbol in symbols:

            cierres_1m = get_cierres(symbol, "1m", 30)
            cierres_5m = get_cierres(symbol, "5m", 30)

            precio = cierres_1m[-1]

            # rango mínimo
            rango = max(cierres_1m[-10:]) - min(cierres_1m[-10:])
            if rango < (0.0015 * precio):
                continue

            # tendencia doble
            if not (tendencia(cierres_1m) and tendencia(cierres_5m)):
                continue

            # pullback real
            if not detectar_pullback(cierres_1m):
                continue

            # evitar máximos
            if precio >= max(cierres_1m[-10:]):
                continue

            s = score(cierres_1m, precio)

            if s > mejor_score:
                mejor_score = s
                mejor = (symbol, precio)

        # ================= ENTRADA =================
        if mejor and mejor_score >= 6:
            symbol_activo, entrada = mejor
            max_precio = entrada
            estado = True

            enviar_alerta(
                f"🚀 ENTRY {symbol_activo}\n{entrada}\nScore: {mejor_score}"
            )

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
