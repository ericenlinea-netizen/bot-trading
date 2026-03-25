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
max_precio = {s: 0 for s in symbols}

ultimo_trade = 0
racha_perdidas = 0
ultima_perdida = False

enviar_alerta("🚀 BOT PRO+ EQUILIBRADO ACTIVO")

while True:
    try:
        for symbol in symbols:

            data = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}").json()
            precio = float(data["price"])

            precios[symbol].append(precio)

            if len(precios[symbol]) > 50:
                precios[symbol].pop(0)

            if len(precios[symbol]) < 20:
                continue

            p = precios[symbol]

            # 🔥 FILTRO VOLATILIDAD (más flexible)
            rango = max(p[-15:]) - min(p[-15:])
            if rango < (0.001 * precio):
                continue

            # 🔥 DIRECCIÓN (menos exigente)
            direccion = abs(p[-1] - p[-10])
            if direccion < (0.0007 * precio):
                continue

            # 🔥 COOLDOWN
            cooldown = 10 if ultima_perdida else 5
            if time.time() - ultimo_trade < cooldown:
                continue

            # 🔥 CONTROL DE RACHAS
            if racha_perdidas >= 3:
                enviar_alerta("⛔ PAUSA POR PERDIDAS")
                time.sleep(20)
                racha_perdidas = 0
                continue

            # ================= ENTRADA =================
            if not estado[symbol]:

                tendencia = p[-1] > p[-2] > p[-3]
                impulso = (p[-1] - p[-6]) > (0.0007 * precio)
                retroceso = p[-2] > p[-3] and p[-1] > p[-2]

                maximo = max(p[-15:])
                no_pico = p[-1] < maximo * 0.999

                if tendencia and impulso and retroceso and no_pico:
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

                trailing = 0.002 * precio

                if max_precio[symbol] - precio >= trailing and ganancia > 0:
                    enviar_alerta(f"💰 {symbol}\nSALIDA: {precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False
                    racha_perdidas = 0

                elif ganancia >= (0.006 * precio):
                    enviar_alerta(f"💰 {symbol}\nTAKE PROFIT\n{precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False
                    racha_perdidas = 0

                elif ganancia <= -(0.002 * precio):
                    enviar_alerta(f"🛑 {symbol}\nSTOP: {precio}\n{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = True
                    racha_perdidas += 1

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
