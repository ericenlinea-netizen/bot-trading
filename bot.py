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
racha_perdidas = 0

enviar_alerta("🔥 BOT PRO VERSIÓN ESTABLE + PRECISA")

while True:
    try:
        data = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        ).json()

        precio = float(data["price"])
        precios.append(precio)

        if len(precios) > 25:
            precios.pop(0)

        if len(precios) < 8:
            time.sleep(1)
            continue

        p = precios

        # ================= FILTRO DE MERCADO =================
        rango = max(p[-10:]) - min(p[-10:])
        if rango < (0.0008 * precio):
            time.sleep(1)
            continue

        # ================= COOLDOWN =================
        cooldown = 6 if ultima_perdida else 4
        if time.time() - ultimo_trade < cooldown:
            time.sleep(1)
            continue

        # ================= CONTROL DE RACHAS =================
        if racha_perdidas >= 3:
            enviar_alerta("⛔ PAUSA POR RACHAS NEGATIVAS")
            time.sleep(20)
            racha_perdidas = 0
            continue

        # ================= ENTRADA =================
        if not estado:

            tendencia = p[-1] > p[-2] > p[-3]
            impulso = (p[-1] - p[-4]) > (0.0004 * precio)

            # evitar comprar en el pico
            maximo = max(p[-10:])
            no_pico = p[-1] < maximo * 0.999

            if tendencia and impulso and no_pico:
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

            tp = 0.0025 * precio
            sl = 0.0018 * precio
            trailing = 0.0012 * precio

            # trailing stop
            if max_precio - precio >= trailing and ganancia > 0:
                enviar_alerta(f"💰 TRAILING\n{precio}\n+{ganancia}")
                estado = False
                ultima_perdida = False
                racha_perdidas = 0

            elif ganancia >= tp:
                enviar_alerta(f"💰 TAKE PROFIT\n{precio}\n+{ganancia}")
                estado = False
                ultima_perdida = False
                racha_perdidas = 0

            elif ganancia <= -sl:
                enviar_alerta(f"🛑 STOP LOSS\n{precio}\n{ganancia}")
                estado = False
                ultima_perdida = True
                racha_perdidas += 1

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
