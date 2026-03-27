import requests
import time

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

symbol = "ETHUSDT"

estado = False
entrada = 0
max_precio = 0
ultimo_trade = 0

enviar_alerta("🔥 BOT VELAS (MOMENTUM REAL) ACTIVO")

while True:
    try:
        # 🔥 OBTENER VELAS (1 minuto)
        data = requests.get(
            f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=10"
        ).json()

        cierres = [float(x[4]) for x in data]

        precio = cierres[-1]

        # ================= COOLDOWN =================
        if time.time() - ultimo_trade < 10:
            time.sleep(2)
            continue

        # ================= DETECTAR MOMENTUM =================
        velas_suben = cierres[-1] > cierres[-2] > cierres[-3]
        impulso = (cierres[-1] - cierres[-4]) > (0.0005 * precio)

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

            tp = 0.003 * precio
            sl = 0.002 * precio
            trailing = 0.0015 * precio

            if max_precio - precio >= trailing and ganancia > 0:
                enviar_alerta(f"💰 TRAILING\n{precio}\n+{ganancia}")
                estado = False

            elif ganancia >= tp:
                enviar_alerta(f"💰 TP\n{precio}\n+{ganancia}")
                estado = False

            elif ganancia <= -sl:
                enviar_alerta(f"🛑 SL\n{precio}\n{ganancia}")
                estado = False

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
