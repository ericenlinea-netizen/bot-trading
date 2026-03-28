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
symbol = "ETHUSDT"

estado = False
entrada = 0
max_precio = 0
ultimo_trade = 0

racha_perdidas = 0

enviar_alerta("🔥 BOT FINAL PRO MAX (CORREGIDO)")

while True:
    try:
        # ================= OBTENER VELAS =================
        data = requests.get(
            f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=15"
        ).json()

        cierres = [float(x[4]) for x in data]
        precio = cierres[-1]

        # ================= BLOQUEO POR RACHAS =================
        if racha_perdidas >= 2:
            enviar_alerta("⛔ PAUSA POR 2 PÉRDIDAS SEGUIDAS")
            time.sleep(60)
            racha_perdidas = 0
            continue

        # ================= COOLDOWN =================
        if time.time() - ultimo_trade < 10:
            time.sleep(2)
            continue

        # ================= FILTRO DE MERCADO =================
        rango = max(cierres[-10:]) - min(cierres[-10:])
        if rango < (0.001 * precio):
            time.sleep(2)
            continue

        # ================= MOMENTUM REAL =================
        velas_suben = cierres[-1] > cierres[-2] > cierres[-3]
        impulso = (cierres[-1] - cierres[-5]) > (0.0007 * precio)

        # ================= FILTRO ANTI-PICO =================
        subida_total = (cierres[-1] - cierres[-6]) / precio
        if subida_total > 0.0025:
            time.sleep(2)
            continue

        # ================= ENTRADA =================
        if not estado:
            if velas_suben and impulso:
                entrada = precio
                max_precio = precio
                estado = True
                ultimo_trade = time.time()

                enviar_alerta(f"🚀 ENTRADA\n{precio}")

        # ================= GESTIÓN =================
        if estado:

            ganancia = precio - entrada

            if precio > max_precio:
                max_precio = precio

            tp = 0.004 * precio
            sl = 0.0015 * precio
            trailing = 0.0025 * precio

            # TRAILING
            if max_precio - precio >= trailing and ganancia > 0:
                enviar_alerta(f"💰 TRAILING\n{precio}\n+{ganancia}")
                estado = False
                racha_perdidas = 0
                time.sleep(20)

            # TAKE PROFIT
            elif ganancia >= tp:
                enviar_alerta(f"💰 TAKE PROFIT\n{precio}\n+{ganancia}")
                estado = False
                racha_perdidas = 0
                time.sleep(30)

            # STOP LOSS
            elif ganancia <= -sl:
                enviar_alerta(f"🛑 STOP LOSS\n{precio}\n{ganancia}")
                estado = False
                racha_perdidas += 1

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
