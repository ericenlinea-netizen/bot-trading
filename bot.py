import requests
import time
enviar_alerta("🔥 PRUEBA BOT FUNCIONANDO")

# ================= TELEGRAM =================
TOKEN = "8772294732:AAGU62SChVJfmwf9RpweG-inBGAjIDlMwms"
CHAT_ID = "5019372975"

def enviar_alerta(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje
    }

    try:
        requests.post(url, data=payload)
    except:
        pass

# ================= BINANCE =================
url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

precios = []

# estados BOT1
en_operacion_1 = False
precio_entrada_1 = 0
max_precio_1 = 0

# estados BOT2
en_operacion_2 = False
precio_entrada_2 = 0

# mensaje inicial
enviar_alerta("🤖 BOT INICIADO Y FUNCIONANDO 24/7")

while True:
    try:
        response = requests.get(url)
        data = response.json()

        precio = float(data["price"])
        precios.append(precio)

        if len(precios) > 20:
            precios.pop(0)

        # ================= BOT 1 (SEGURO) =================
        if len(precios) >= 10 and not en_operacion_1:
            rango = max(precios[-10:]) - min(precios[-10:])
            tendencia_valida = rango > 25

            if tendencia_valida:
                p1, p2, p3, p4, p5, p6 = precios[-6:]
                max_reciente = max(precios[-10:])

                if p6 >= max_reciente:
                    if p1 < p2 < p3 and p4 < p3 and p5 < p4 and p6 > p5:
                        enviar_alerta(f"🟢 BOT1 ENTRADA LONG en {p6}")
                        en_operacion_1 = True
                        precio_entrada_1 = p6
                        max_precio_1 = p6

        if en_operacion_1:
            ganancia = precio - precio_entrada_1

            if precio > max_precio_1:
                max_precio_1 = precio

            # trailing stop
            if max_precio_1 - precio >= 4 and ganancia > 6:
                enviar_alerta(f"💰 BOT1 SALIDA en {precio} (+{ganancia})")
                en_operacion_1 = False

            elif ganancia <= -10:
                enviar_alerta(f"🛑 BOT1 STOP en {precio} ({ganancia})")
                en_operacion_1 = False

        # ================= BOT 2 (RÁPIDO) =================
        if len(precios) >= 5 and not en_operacion_2:
            p1, p2, p3, p4, p5 = precios[-5:]

            if p3 > p2 > p1 and p5 > p4:
                enviar_alerta(f"⚡ BOT2 ENTRADA en {p5}")
                en_operacion_2 = True
                precio_entrada_2 = p5

        if en_operacion_2:
            ganancia = precio - precio_entrada_2

            if ganancia >= 8:
                enviar_alerta(f"💰 BOT2 TP en {precio} (+{ganancia})")
                en_operacion_2 = False

            elif ganancia <= -8:
                enviar_alerta(f"🛑 BOT2 STOP en {precio} ({ganancia})")
                en_operacion_2 = False

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
