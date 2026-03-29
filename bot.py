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

estado = False
entrada = 0
max_precio = 0
ultimo_trade = 0

racha_perdidas = 0
ganancia_acumulada = 0

enviar_alerta("🔥 BOT FINAL MEJORADO ACTIVO")

while True:
    try:
        # ================= OBTENER DATOS =================
        data = requests.get(
            f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=30"
        ).json()

        cierres = [float(x[4]) for x in data]
        precio = cierres[-1]

        # ================= PROTECCIÓN DE GANANCIA =================
        if ganancia_acumulada >= 2:  # ajusta a tu capital (ej: 2 USDT)
            enviar_alerta("🛑 PROTECCIÓN DE GANANCIA ACTIVADA")
            time.sleep(120)
            ganancia_acumulada = 0
            continue

        # ================= BLOQUEO POR RACHAS =================
        if racha_perdidas >= 2:
            enviar_alerta("⛔ PAUSA POR 2 PÉRDIDAS SEGUIDAS")
            time.sleep(60)
            racha_perdidas = 0
            continue

        # ================= COOLDOWN =================
        if time.time() - ultimo_trade < 10:
            time.sleep(2)
            continue

        # ================= FILTRO DE MERCADO =================
        rango = max(cierres[-10:]) - min(cierres[-10:])
        if rango < (0.0015 * precio):
            time.sleep(2)
            continue

        # ================= TENDENCIA =================
        media_corta = sum(cierres[-5:]) / 5
        media_larga = sum(cierres[-15:]) / 15
        tendencia_alcista = media_corta > media_larga

        # ================= MOMENTUM =================
        velas_suben = cierres[-1] > cierres[-2] > cierres[-3]
        impulso = (cierres[-1] - cierres[-5]) > (0.0006 * precio)
        fuerza = (cierres[-1] - cierres[-2]) > (0.0003 * precio)

        # ================= FILTRO ANTI-PICO =================
        subida_total = (cierres[-1] - cierres[-6]) / precio
        if subida_total > 0.003:
            time.sleep(2)
            continue

        # ================= ENTRADA =================
        if not estado:
            if velas_suben and impulso and tendencia_alcista and fuerza:
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

            # Parámetros optimizados
            tp = 0.004 * precio        # 0.4%
            sl = 0.0025 * precio      # 0.25%
            trailing = 0.0018 * precio  # trailing más agresivo

            # ================= TRAILING =================
            if max_precio - precio >= trailing and ganancia > 0:
                enviar_alerta(f"💰 TRAILING\n{precio}\n+{ganancia:.4f}")
                estado = False
                racha_perdidas = 0
                ganancia_acumulada += ganancia
                time.sleep(20)

            # ================= TAKE PROFIT =================
            elif ganancia >= tp:
                enviar_alerta(f"💰 TAKE PROFIT\n{precio}\n+{ganancia:.4f}")
                estado = False
                racha_perdidas = 0
                ganancia_acumulada += ganancia
                time.sleep(30)

            # ================= STOP LOSS =================
            elif ganancia <= -sl:
                enviar_alerta(f"🛑 STOP LOSS\n{precio}\n{ganancia:.4f}")
                estado = False
                racha_perdidas += 1

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
