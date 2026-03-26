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

symbols = ["BTCUSDT", "ETHUSDT"]

precios = {s: [] for s in symbols}
estado = {s: False for s in symbols}
entrada = {s: 0 for s in symbols}

ultimo_trade = 0
ultima_perdida = False

enviar_alerta("🔥 BOT SCALPING ACTIVO")

while True:
    try:
        for symbol in symbols:

            data = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}").json()
            precio = float(data["price"])

            precios[symbol].append(precio)

            if len(precios[symbol]) > 30:
                precios[symbol].pop(0)

            if len(precios[symbol]) < 10:
                continue

            p = precios[symbol]

            # ================= COOLDOWN =================
            cooldown = 6 if ultima_perdida else 3
            if time.time() - ultimo_trade < cooldown:
                continue

            # ================= ENTRADA SIMPLE =================
            if not estado[symbol]:

                # micro tendencia
                tendencia = p[-1] > p[-2]

                # pequeño impulso
                impulso = (p[-1] - p[-3]) > (0.0003 * precio)

                if tendencia and impulso:
                    entrada[symbol] = precio
                    estado[symbol] = True
                    ultimo_trade = time.time()

                    enviar_alerta(f"🚀 {symbol}\nENTRADA: {precio}")

            # ================= GESTIÓN =================
            if estado[symbol]:

                ganancia = precio - entrada[symbol]

                tp = 0.002 * precio
                sl = 0.0015 * precio

                if ganancia >= tp:
                    enviar_alerta(f"💰 {symbol}\nGANANCIA\n{precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False

                elif ganancia <= -sl:
                    enviar_alerta(f"🛑 {symbol}\nSTOP\n{precio}\n{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = True

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
