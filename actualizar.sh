#!/bin/bash
#
# Actualización diaria de Cero Vagos.
#
# Busca los avisos publicados en los últimos 2 días, los filtra, saca de la web
# los que ya pasaron los 2 meses y regenera datos/ofertas.js.
#
# Se usan 2 días y no 1 a propósito: si una corrida falla o la computadora
# estaba apagada, al día siguiente se recupera lo que se perdió.
#
# Correr a mano:      ./actualizar.sh
# Ver qué pasó:       tail -f datos/actualizacion.log
#
# Para que corra solo cada medianoche (hora de Perú), ver el final del archivo.

set -u

cd "$(dirname "$0")" || exit 1

REGISTRO="datos/actualizacion.log"
mkdir -p datos

# tee: se ve en pantalla y queda en el registro. Cuando corre solo de noche
# nadie mira la pantalla, pero cuando lo corres a mano querés ver qué pasa.
{
  echo ""
  echo "════════════════════════════════════════════════════════"
  echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "════════════════════════════════════════════════════════"

  python3 -u -m motor recolectar --publicas --dias 2 --limite 60 --exportar
  ESTADO=$?

  if [ $ESTADO -eq 0 ]; then
    python3 -u -m motor stats
  else
    echo "!! La recolección terminó con error (código $ESTADO)"
  fi
} 2>&1 | tee -a "$REGISTRO"

# Deja el registro en un tamaño razonable (últimas 2000 líneas).
tail -n 2000 "$REGISTRO" > "$REGISTRO.tmp" && mv "$REGISTRO.tmp" "$REGISTRO"

# ---------------------------------------------------------------------------
# Para programarlo en tu Mac, una sola vez:
#
#   chmod +x actualizar.sh
#   crontab -e
#
# y pega esta línea (00:00 de la zona horaria de tu Mac; si tu Mac está en
# hora de Perú, es medianoche peruana):
#
#   0 0 * * * cd ~/Desktop/cero-vagos && ./actualizar.sh
#
# Ojo: la computadora tiene que estar encendida a esa hora. Si se apaga de
# noche, conviene programarlo a una hora en la que sí esté prendida, o mover
# el motor a un servidor cuando el sitio salga a producción.
# ---------------------------------------------------------------------------
