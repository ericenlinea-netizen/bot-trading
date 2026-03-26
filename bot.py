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
symbols = ["ETHUSDT", "BNBUSDT", "SOLUSDT"]

precios = {s: [] for s in symbols}
estado = {s: False for s in symbols}
entrada = {s: 0 for s in symbols}
max_precio = {s: 0 for s in symbols}

ultimo_trade = 0
ultima_perdida = False
racha_perdidas = 0

enviar_alerta("🔥 BOT PRO MULTI-CRIPTO ACTIVO (ETH + BNB + SOL)")

while True:
    try:
        for symbol in symbols:

            data = requests.get(
                f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            ).json()

            precio = float(data["price"])

            precios[symbol].append(precio)

            if len(precios[symbol]) > 30:
                precios[symbol].pop(0)

            if len(precios[symbol]) < 10:
                continue

            p = precios[symbol]

            # ================= FILTRO MERCADO =================
            rango = max(p[-10:]) - min(p[-10:])
            if rango < (0.0008 * precio):
                continue

            # ================= COOLDOWN =================
            cooldown = 8 if ultima_perdida else 5
            if time.time() - ultimo_trade < cooldown:
                continue

            # ================= CONTROL DE RACHAS =================
            if racha_perdidas >= 3:
                enviar_alerta("⛔ PAUSA POR RACHAS NEGATIVAS")
                time.sleep(20)
                racha_perdidas = 0
                continue

            # ================= ENTRADA =================
            if not estado[symbol]:

                tendencia = p[-1] > p[-2]
                impulso = (p[-1] - p[-4]) > (0.0005 * precio)

                # evitar entrar en picos
                maximo = max(p[-10:])
                no_pico = p[-1] < maximo * 0.999

                if tendencia and impulso and no_pico:
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

                # 🔥 CONFIG GLOBAL OPTIMIZADA
                tp = 0.0025 * precio
                sl = 0.0018 * precio

                trailing = 0.0015 * precio

                # trailing stop (deja correr ganancias)
                if max_precio[symbol] - precio >= trailing and ganancia > 0:
                    enviar_alerta(f"💰 {symbol}\nSALIDA TRAILING\n{precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False
                    racha_perdidas = 0

                elif ganancia >= tp:
                    enviar_alerta(f"💰 {symbol}\nTAKE PROFIT\n{precio}\n+{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = False
                    racha_perdidas = 0

                elif ganancia <= -sl:
                    enviar_alerta(f"🛑 {symbol}\nSTOP\n{precio}\n{ganancia}")
                    estado[symbol] = False
                    ultima_perdida = True
                    racha_perdidas += 1

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
