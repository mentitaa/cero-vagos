#!/bin/bash
#
# Corrida larga de Cero Vagos, para dejar trabajando de madrugada.
#
#   ./noche.sh
#
# Recolecta primero las convocatorias del Estado (rápido, sin navegador) y
# después los portales privados (lento, con navegador). Al terminar exporta al
# sitio y deja todo anotado.
#
# Usa `caffeinate`, que viene con macOS: mientras el script corre, la Mac no se
# duerme sola. OJO: si cierras la tapa, se suspende igual. Déjala enchufada y
# con la tapa abierta.
#
# Se puede cortar con Ctrl-C sin miedo: cada oferta se guarda apenas se
# procesa, así que lo recolectado hasta ese momento no se pierde.

set -u
cd "$(dirname "$0")" || exit 1
mkdir -p datos

REGISTRO="datos/noche-$(date +%Y-%m-%d_%H%M).log"

# Cuántos avisos pedir por fuente. Súbelos si quieres una corrida más larga.
LIMITE_PUBLICO=200
LIMITE_PRIVADO=600

echo "Cero Vagos · corrida larga"
echo "Inicio:   $(date '+%Y-%m-%d %H:%M:%S')"
echo "Registro: $REGISTRO"
echo "La Mac no se dormirá mientras esto corra. No cierres la tapa."
echo

# caffeinate -i  evita que se duerma por inactividad
#            -s  evita la suspensión del sistema mientras esté enchufada
caffeinate -is bash <<SCRIPT 2>&1 | tee -a "$REGISTRO"
  echo "════════════════════════════════════════════════════════"
  echo "  CONVOCATORIAS DEL ESTADO · \$(date '+%H:%M:%S')"
  echo "════════════════════════════════════════════════════════"
  python3 -u -m motor recolectar --publicas --limite $LIMITE_PUBLICO --exportar

  echo
  echo "════════════════════════════════════════════════════════"
  echo "  PORTALES PRIVADOS · \$(date '+%H:%M:%S')"
  echo "════════════════════════════════════════════════════════"
  python3 -u -m motor recolectar --limite $LIMITE_PRIVADO --exportar

  echo
  echo "════════════════════════════════════════════════════════"
  echo "  ESTADO DE LA BASE · \$(date '+%H:%M:%S')"
  echo "════════════════════════════════════════════════════════"
  python3 -u -m motor stats
SCRIPT

echo
echo "Fin: $(date '+%Y-%m-%d %H:%M:%S')"
echo
echo "Para ver el resumen sin leer todo el registro:"
echo "  grep -E 'RESUMEN|Pasaron|Avisos leídos|exportadas' \"$REGISTRO\""
echo
echo "Y para ver las ofertas: abre index.html"
