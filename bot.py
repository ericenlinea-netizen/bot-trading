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

precios = []
estado = False
entrada = 0
max_precio = 0

ultimo_trade = 0
ultima_perdida = False

enviar_alerta("🚀 BOT TENDENCIA + RETROCESO ACTIVO")

while True:
    try:
        data = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        ).json()

        precio = float(data["price"])
        precios.append(precio)

        if len(precios) > 30:
            precios.pop(0)

        if len(precios) < 15:
            time.sleep(1)
            continue

        p = precios

        # ================= DETECTAR TENDENCIA =================
        tendencia = p[-1] > p[-5] > p[-10]

        # ================= DETECTAR RETROCESO =================
        retroceso = p[-3] > p[-2] and p[-2] > p[-1]

        # ================= REANUDACIÓN =================
        rebote = p[-1] > p[-2]

        # ================= COOLDOWN =================
        cooldown = 8 if ultima_perdida else 5
        if time.time() - ultimo_trade < cooldown:
            time.sleep(1)
            continue

        # ================= ENTRADA =================
        if not estado:

            if tendencia and retroceso and rebote:
                entrada = precio
                max_precio = precio
                estado = True
                ultimo_trade = time.time()

                enviar_alerta(f"🚀 ENTRADA (RETEST)\n{precio}")

        # ================= GESTIÓN =================
        if estado:

            ganancia = precio - entrada

            if precio > max_precio:
                max_precio = precio

            tp = 0.003 * precio
            sl = 0.0018 * precio
            trailing = 0.0015 * precio

            # trailing
            if max_precio - precio >= trailing and ganancia > 0:
                enviar_alerta(f"💰 TRAILING\n{precio}\n+{ganancia}")
                estado = False
                ultima_perdida = False

            elif ganancia >= tp:
                enviar_alerta(f"💰 TAKE PROFIT\n{precio}\n+{ganancia}")
                estado = False
                ultima_perdida = False

            elif ganancia <= -sl:
                enviar_alerta(f"🛑 STOP LOSS\n{precio}\n{ganancia}")
                estado = False
                ultima_perdida = True

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
