import requests
import time

# ================= TELEGRAM =================
TOKEN = "8772294732:AAGU62SChVJfmwf9RpweG-inBGAjIDlMwms"
CHAT_ID = "5019372975"

def enviar_alerta(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=payload)
    except:
        pass

# ================= BINANCE =================
url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

precios = []

# estados
en_operacion = False
precio_entrada = 0
max_precio = 0

# control inteligente
ultimo_trade = 0
cooldown = 5
ultima_fue_perdida = False
racha_perdidas = 0

enviar_alerta("🤖 BOT PRO ACTIVO 🚀")

while True:
    try:
        data = requests.get(url).json()
        precio = float(data["price"])
        precios.append(precio)

        if len(precios) > 30:
            precios.pop(0)

        # ================= FILTRO DE VOLATILIDAD =================
        operar = True
        if len(precios) >= 10:
            rango = max(precios[-10:]) - min(precios[-10:])
            if rango < 20:
                operar = False

        # ================= COOLDOWN DINÁMICO =================
        if ultima_fue_perdida:
            cooldown = 10
        else:
            cooldown = 5

        if time.time() - ultimo_trade < cooldown:
            time.sleep(1)
            continue

        # ================= CONTROL DE RACHAS =================
        if racha_perdidas >= 3:
            enviar_alerta("⛔ PAUSA POR RACHAS NEGATIVAS")
            time.sleep(15)
            racha_perdidas = 0
            continue

        # ================= ENTRADA =================
        if operar and len(precios) >= 6 and not en_operacion:

            p1, p2, p3, p4, p5, p6 = precios[-6:]

            # tendencia clara
            tendencia = p6 > p5 > p4

            # impulso real
            impulso = (p6 - p3) > 8

            # anti-FOMO (no entrar en máximos extremos)
            max_reciente = max(precios[-10:])
            no_fomo = p6 < max_reciente - 2

            if tendencia and impulso and no_fomo:
                enviar_alerta(f"🚀 ENTRADA LONG\nPrecio: {p6}")
                en_operacion = True
                precio_entrada = p6
                max_precio = p6
                ultimo_trade = time.time()

        # ================= GESTIÓN =================
        if en_operacion:
            ganancia = precio - precio_entrada

            if precio > max_precio:
                max_precio = precio

            # trailing mejorado
            if max_precio - precio >= 5 and ganancia > 6:
                enviar_alerta(f"💰 GANANCIA\nSalida: {precio}\n+{ganancia}")
                en_operacion = False
                ultima_fue_perdida = False
                racha_perdidas = 0

            elif ganancia >= 12:
                enviar_alerta(f"💰 TAKE PROFIT\nSalida: {precio}\n+{ganancia}")
                en_operacion = False
                ultima_fue_perdida = False
                racha_perdidas = 0

            elif ganancia <= -10:
                enviar_alerta(f"🛑 STOP LOSS\nSalida: {precio}\n{ganancia}")
                en_operacion = False
                ultima_fue_perdida = True
                racha_perdidas += 1

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
