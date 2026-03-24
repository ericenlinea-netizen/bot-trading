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

# ================= CONFIG =================
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]

precios = {s: [] for s in symbols}
estado = {s: False for s in symbols}
entrada = {s: 0 for s in symbols}
max_precio = {s: 0 for s in symbols}

ultimo_trade = 0
racha_perdidas = 0
ultima_perdida = False

enviar_alerta("🚀 BOT MULTI-CRIPTO ACTIVO (modo equilibrado)")

while True:
    try:
        for symbol in symbols:

            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            data = requests.get(url).json()
            precio = float(data["price"])

            precios[symbol].append(precio)

            if len(precios[symbol]) > 40:
                precios[symbol].pop(0)

            if len(precios[symbol]) < 15:
                continue

            p = precios[symbol]

            # ================= FILTRO VOLATILIDAD (AJUSTADO) =================
            rango = max(p[-10:]) - min(p[-10:])
            if rango < (0.0005 * precio):
                continue

            # ================= COOLDOWN DINÁMICO =================
            cooldown = 8 if ultima_perdida else 4
            if time.time() - ultimo_trade < cooldown:
                continue

            # ================= BLOQUEO POR RACHAS =================
            if racha_perdidas >= 3:
                enviar_alerta("⛔ PAUSA GLOBAL POR PERDIDAS")
                time.sleep(15)
                racha_perdidas = 0
                continue

            # ================= ENTRADA =================
            if not estado[symbol]:

                tendencia = p[-1] > p[-2] > p[-3]
                impulso = (p[-1] - p[-5]) > (0.0005 * precio)
                retroceso = p[-2] > p[-3] and p[-1] > p[-2]

                maximo = max(p[-10:])
                no_pico = p[-1] < maximo * 0.9995

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

                trailing = 0.0015 * precio  # más ajustado

                if max_precio[symbol] - precio >= trailing and ganancia > 0:
                    enviar_alerta(f"💰 {symbol}\nSALIDA: {precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False
                    racha_perdidas = 0

                elif ganancia >= (0.003 * precio):
                    enviar_alerta(f"💰 {symbol}\nTAKE PROFIT\n{precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False
                    racha_perdidas = 0

                elif ganancia <= -(0.0015 * precio):
                    enviar_alerta(f"🛑 {symbol}\nSTOP: {precio}\n{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = True
                    racha_perdidas += 1

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
