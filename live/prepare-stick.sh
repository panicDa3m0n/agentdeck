#!/usr/bin/env bash
# Prepara dal Mac la chiavetta di avvio per la Steam Deck: FAT32 con il contenuto dell'ISO ufficiale
# di Arch, voce di boot che punta all'etichetta della chiavetta ed esegue agent/live-setup.sh.
#
# Uso:  live/prepare-stick.sh diskN            (CANCELLA diskN: deve essere un disco USB esterno)
#       DRY_RUN=1 live/prepare-stick.sh diskN  (solo controlli, nessuna scrittura)
#
# Documentazione: docs/chiavetta-live.md

set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
ISO="$ROOT/cache/archlinux-2026.10.01-x86_64.iso"
ISO_SHA256=684ded26c63240ff4a41e8c25ee84ea6da233f557364821f13d12c2b0a9059a5
LABEL=ARCH_202610
# copytoram=n: con RAM sufficiente archiso copierebbe il sistema in memoria e smonterebbe la chiavetta,
# rendendo irraggiungibile agent/live-setup.sh quando parte su tty1
SCRIPT_PARAM="copytoram=n script=/run/archiso/bootmnt/agent/live-setup.sh"
DISK=/dev/${1:?specifica il disco, es. disk4}

die() { echo "ERRORE: $*" >&2; exit 1; }
key() { diskutil info -plist "$DISK" | plutil -extract "$1" raw -o - - 2>/dev/null; }

# --- Controlli: solo un disco USB esterno intero, di dimensione plausibile per una chiavetta
diskutil info "$DISK" >/dev/null 2>&1 || die "$DISK non esiste"
[[ $(key WholeDisk) == true ]]  || die "$DISK non è un disco intero"
[[ $(key Internal) == false ]]  || die "$DISK è un disco interno"
[[ $(key BusProtocol) == USB ]] || die "$DISK non è un dispositivo USB ($(key BusProtocol))"
size=$(key Size)
(( size <= 256 * 1000**3 ))     || die "$DISK è più grande di 256 GB: non sembra una chiavetta"
(( size >= 4 * 1000**3 ))       || die "$DISK è più piccolo di 4 GB"

WIFI_SSID=$(sed -n 's/^WIFI_SSID=//p' "$ROOT/secrets/wifi.env" | head -1)
WIFI_PASS=$(sed -n 's/^WIFI_PASS=//p' "$ROOT/secrets/wifi.env" | head -1)
[[ -n $WIFI_SSID && -n $WIFI_PASS ]] || die "compila WIFI_SSID e WIFI_PASS in secrets/wifi.env"

echo "Disco: $DISK - $(key MediaName) - $((size / 1000**3)) GB - USB esterno"
echo "Rete Wi-Fi: $WIFI_SSID"

echo "Verifica ISO..."
echo "$ISO_SHA256  $ISO" | shasum -a 256 -c --quiet || die "checksum ISO non valido"

if [[ ${DRY_RUN:-0} == 1 ]]; then echo "DRY_RUN: controlli superati, nessuna scrittura."; exit 0; fi

# --- Scrittura
diskutil eraseDisk FAT32 "$LABEL" MBRFormat "$DISK"
VOL="/Volumes/$LABEL"
[[ -d $VOL ]] || die "volume $VOL non montato"
mdutil -i off "$VOL" >/dev/null 2>&1 || true
touch "$VOL/.metadata_never_index"

ISO_MNT=$(mktemp -d)
ISO_DEV=$(hdiutil attach -nomount -readonly -imagekey diskimage-class=CRawDiskImage "$ISO" | awk 'NR==1{print $1}')
trap 'umount "$ISO_MNT" 2>/dev/null; hdiutil detach "$ISO_DEV" >/dev/null 2>&1 || true' EXIT
mount -t cd9660 -r "$ISO_DEV" "$ISO_MNT"

echo "Copia del contenuto dell'ISO (qualche minuto)..."
cp -RX "$ISO_MNT"/ "$VOL"/
chmod -R u+w "$VOL"

# Boot per etichetta (la chiavetta FAT32 non ha l'UUID dell'ISO) e script dell'agente nella voce principale
for f in "$VOL"/loader/entries/*.conf; do
  sed -i '' -E "s/archisosearchuuid=[^ ]+/archisolabel=$LABEL/" "$f"
done
sed -i '' -E "/^options/ s|[[:space:]]*\$| $SCRIPT_PARAM|" "$VOL/loader/entries/01-archiso-linux.conf"
sed -i '' -E "s/^timeout .*/timeout 3/" "$VOL/loader/loader.conf"

mkdir -p "$VOL/agent"
cp -X "$ROOT/live/live-setup.sh" "$ROOT/live/authorized_keys" "$ROOT/secrets/wifi.env" "$VOL/agent/"

rm -rf "$VOL"/.fseventsd "$VOL"/.Spotlight-V100
dot_clean -m "$VOL"

echo "--- Voce di boot"
grep options "$VOL/loader/entries/01-archiso-linux.conf"
sync
diskutil eject "$DISK"
echo "Chiavetta pronta."
