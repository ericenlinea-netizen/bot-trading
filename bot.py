import requests
import time

# ================= TELEGRAM =================
TOKEN = "8772294732:AAGU62SChVJfmwf9RpweG-inBGAjIDlMwms"
CHAT_ID = "5019372975"

def enviar_alerta(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

# ================= BINANCE =================
url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

precios = []

# estado
en_trade = False
entrada = 0
max_precio = 0

# control
ultimo_trade = 0
racha_perdidas = 0
ultima_perdida = False

enviar_alerta("🔥 BOT PRO V2 ACTIVO")

while True:
    try:
        data = requests.get(url).json()
        precio = float(data["price"])
        precios.append(precio)

        if len(precios) > 40:
            precios.pop(0)

        if len(precios) < 15:
            time.sleep(1)
            continue

        # ================= FILTRO VOLATILIDAD =================
        rango = max(precios[-10:]) - min(precios[-10:])
        if rango < 25:
            time.sleep(1)
            continue

        # ================= COOLDOWN =================
        cooldown = 12 if ultima_perdida else 6
        if time.time() - ultimo_trade < cooldown:
            time.sleep(1)
            continue

        # ================= BLOQUEO POR PERDIDAS =================
        if racha_perdidas >= 3:
            enviar_alerta("⛔ BLOQUEO TEMPORAL (rachas)")
            time.sleep(20)
            racha_perdidas = 0
            continue

        # ================= ENTRADA INTELIGENTE =================
        if not en_trade:

            # tendencia fuerte
            tendencia = precios[-1] > precios[-2] > precios[-3] > precios[-4]

            # impulso fuerte
            impulso = (precios[-1] - precios[-5]) > 12

            # retroceso (clave para duplicar ganancias)
            retroceso = precios[-2] > precios[-3] and precios[-1] > precios[-2]

            # evitar picos
            maximo = max(precios[-10:])
            no_pico = precios[-1] < maximo - 3

            if tendencia and impulso and retroceso and no_pico:
                entrada = precio
                max_precio = precio
                en_trade = True
                ultimo_trade = time.time()

                enviar_alerta(f"🚀 ENTRADA PRO\n{precio}")

        # ================= GESTIÓN AVANZADA =================
        if en_trade:

            ganancia = precio - entrada

            if precio > max_precio:
                max_precio = precio

            # trailing dinámico (DEJA CORRER GANANCIAS)
            trailing = 6 if ganancia > 15 else 4

            if max_precio - precio >= trailing and ganancia > 8:
                enviar_alerta(f"💰 TRAILING EXIT\n{precio}\n+{ganancia}")
                en_trade = False
                ultima_perdida = False
                racha_perdidas = 0

            elif ganancia >= 25:
                enviar_alerta(f"💰 TAKE PROFIT GRANDE\n{precio}\n+{ganancia}")
                en_trade = False
                ultima_perdida = False
                racha_perdidas = 0

            elif ganancia <= -10:
                enviar_alerta(f"🛑 STOP LOSS\n{precio}\n{ganancia}")
                en_trade = False
                ultima_perdida = True
                racha_perdidas += 1

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
