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

# 🔥 SOLO ETH (el que funciona)
symbols = ["ETHUSDT"]

precios = {s: [] for s in symbols}
estado = {s: False for s in symbols}
entrada = {s: 0 for s in symbols}
max_precio = {s: 0 for s in symbols}

ultimo_trade = 0
ultima_perdida = False

enviar_alerta("🔥 BOT FINAL ESTABLE ACTIVO (ETH)")

while True:
    try:
        for symbol in symbols:

            data = requests.get(
                f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            ).json()

            precio = float(data["price"])

            precios[symbol].append(precio)

            if len(precios[symbol]) > 25:
                precios[symbol].pop(0)

            if len(precios[symbol]) < 8:
                continue

            p = precios[symbol]

            # 🔥 COOLDOWN (más flexible)
            cooldown = 6 if ultima_perdida else 3
            if time.time() - ultimo_trade < cooldown:
                continue

            # ================= ENTRADA =================
            if not estado[symbol]:

                tendencia = p[-1] > p[-2]
                impulso = (p[-1] - p[-3]) > (0.00025 * precio)

                if tendencia and impulso:
                    entrada[symbol] = precio
                    max_precio[symbol] = precio
                    estado[symbol] = True
                    ultimo_trade = time.time()

                    enviar_alerta(f"🚀 {symbol}\nENTRADA: {precio}")

            # ================= GESTIÓN =================
            if estado[symbol]:

                ganancia = precio - entrada[symbol]

                if precio > max_precio[symbol]:
                    max_precio[symbol] = precio

                # 🔥 CONFIG PERFECTA ETH
                tp = 0.0022 * precio
                sl = 0.0016 * precio
                trailing = 0.0012 * precio

                # trailing (deja correr)
                if max_precio[symbol] - precio >= trailing and ganancia > 0:
                    enviar_alerta(f"💰 {symbol}\nTRAILING\n{precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False

                elif ganancia >= tp:
                    enviar_alerta(f"💰 {symbol}\nTP\n{precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False

                elif ganancia <= -sl:
                    enviar_alerta(f"🛑 {symbol}\nSL\n{precio}\n{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = True

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
