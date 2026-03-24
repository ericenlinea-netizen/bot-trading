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
symbols = ["BTCUSDT", "ETHUSDT"]

precios = {s: [] for s in symbols}
estado = {s: False for s in symbols}
entrada = {s: 0 for s in symbols}
max_precio = {s: 0 for s in symbols}

ultimo_trade = 0
racha_perdidas = 0
ultima_perdida = False

enviar_alerta("🔥 BOT PRO+ ULTRA AFINADO ACTIVO")

while True:
    try:
        for symbol in symbols:

            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            data = requests.get(url).json()
            precio = float(data["price"])

            precios[symbol].append(precio)

            if len(precios[symbol]) > 60:
                precios[symbol].pop(0)

            if len(precios[symbol]) < 25:
                continue

            p = precios[symbol]

            # ================= FILTRO 1: VOLATILIDAD =================
            rango = max(p[-20:]) - min(p[-20:])
            if rango < (0.0015 * precio):
                continue

            # ================= FILTRO 2: DIRECCIÓN REAL =================
            direccion = abs(p[-1] - p[-15])
            if direccion < (0.001 * precio):
                continue

            # ================= COOLDOWN INTELIGENTE =================
            cooldown = 12 if ultima_perdida else 6
            if time.time() - ultimo_trade < cooldown:
                continue

            # ================= CONTROL DE RACHAS =================
            if racha_perdidas >= 3:
                enviar_alerta("⛔ BLOQUEO POR RACHAS NEGATIVAS")
                time.sleep(25)
                racha_perdidas = 0
                continue

            # ================= ENTRADA PRO =================
            if not estado[symbol]:

                # tendencia fuerte real
                tendencia = p[-1] > p[-2] > p[-3] > p[-4] > p[-5]

                # impulso fuerte
                impulso = (p[-1] - p[-8]) > (0.001 * precio)

                # retroceso limpio (evita FOMO)
                retroceso = p[-3] > p[-4] and p[-1] > p[-2]

                # evitar máximos extremos
                maximo = max(p[-20:])
                no_pico = p[-1] < maximo * 0.997

                if tendencia and impulso and retroceso and no_pico:
                    entrada[symbol] = precio
                    max_precio[symbol] = precio
                    estado[symbol] = True
                    ultimo_trade = time.time()

                    enviar_alerta(f"🚀 {symbol}\nENTRADA: {precio}")

            # ================= GESTIÓN PRO =================
            if estado[symbol]:

                ganancia = precio - entrada[symbol]

                if precio > max_precio[symbol]:
                    max_precio[symbol] = precio

                # trailing inteligente (deja correr más)
                if ganancia > (0.004 * precio):
                    trailing = 0.0015 * precio
                else:
                    trailing = 0.0025 * precio

                # salida por trailing
                if max_precio[symbol] - precio >= trailing and ganancia > 0:
                    enviar_alerta(f"💰 {symbol}\nSALIDA: {precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False
                    racha_perdidas = 0

                # take profit grande (deja correr)
                elif ganancia >= (0.008 * precio):
                    enviar_alerta(f"💰 {symbol}\nTAKE PROFIT GRANDE\n{precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False
                    racha_perdidas = 0

                # stop loss más inteligente
                elif ganancia <= -(0.0025 * precio):
                    enviar_alerta(f"🛑 {symbol}\nSTOP: {precio}\n{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = True
                    racha_perdidas += 1

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
