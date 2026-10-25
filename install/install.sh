#!/usr/bin/env bash
# Installazione di Arch Linux sulla Steam Deck. Si esegue da root nel sistema live, via SSH.
#
# Uso:  install.sh <fase>
# Fasi, in ordine: check | disk | base | config | boot | verify | finish
# "check" e "verify" sono in sola lettura. "disk" CANCELLA il disco e richiede CONFIRM=nvme0n1.

set -euo pipefail

DISK=/dev/nvme0n1
DISK_MODEL="WD PC SN740 SDDPTQE-2T00"
DMI_PRODUCT=Jupiter
ESP=${DISK}p1
ROOT=${DISK}p2
HOST=agentdeck
AGENT=agent
TZ_NAME=Europe/Rome
MNT=/mnt
BTRFS_OPTS=noatime,compress=zstd:1
# subvolume:punto di mount. "@" deve restare il primo
SUBVOLS=("@:/" "@home:/home" "@log:/var/log" "@pkg:/var/cache/pacman/pkg" "@snapshots:/.snapshots")

PACKAGES=(
  base linux linux-lts linux-firmware amd-ucode
  btrfs-progs dosfstools grub efibootmgr grub-btrfs inotify-tools snapper snap-pac
  iwd openssh sudo zram-generator terminus-font
  base-devel git vim jq rsync less htop pciutils usbutils smartmontools man-db
)

die() { echo "ERRORE: $*" >&2; exit 1; }
step() { printf '\n== %s\n' "$*"; }
in_chroot() { arch-chroot "$MNT" /bin/bash -euo pipefail -c "$1"; }

mount_all() {
  local sv
  for sv in "${SUBVOLS[@]}"; do
    mount --mkdir -o "$BTRFS_OPTS,subvol=${sv%%:*}" "$ROOT" "$MNT${sv#*:}"
  done
  mount --mkdir -o umask=0077 "$ESP" "$MNT/efi"
  findmnt -R "$MNT"
}

phase_check() {
  step "Controlli preliminari"
  [[ -d /run/archiso ]] || die "non sono nel sistema live di Arch"
  [[ $(cat /sys/class/dmi/id/product_name) == "$DMI_PRODUCT" ]] || die "questa non è una Steam Deck LCD"
  [[ -d /sys/firmware/efi ]] || die "sistema non avviato in UEFI"
  [[ -b $DISK ]] || die "$DISK non esiste"
  local model
  model=$(sed 's/ *$//' "/sys/block/${DISK#/dev/}/device/model")
  [[ $model == "$DISK_MODEL" ]] || die "modello del disco inatteso: '$model'"
  compgen -G "/var/lib/iwd/*.psk" >/dev/null || die "nessun profilo Wi-Fi salvato da copiare"
  ping -c1 -W3 archlinux.org >/dev/null || die "niente connessione a internet"
  timedatectl set-ntp true
  lsblk -o NAME,SIZE,FSTYPE,LABEL,MODEL "$DISK"
  echo "Controlli OK"
}

phase_disk() {
  [[ ${CONFIRM:-} == "${DISK#/dev/}" ]] || die "fase distruttiva: rilancia con CONFIRM=${DISK#/dev/}"
  phase_check
  step "Cancellazione di $DISK"
  umount -R "$MNT" 2>/dev/null || true
  local p
  for p in "${DISK}"p*; do [[ -b $p ]] && wipefs -af "$p"; done
  wipefs -af "$DISK"
  blkdiscard -f "$DISK" || echo "blkdiscard non riuscito, proseguo"
  sgdisk --zap-all "$DISK"

  step "Partizioni: EFI 2 GiB + Btrfs"
  sgdisk -n1:0:+2G -t1:ef00 -c1:EFI -n2:0:0 -t2:8304 -c2:"$HOST" "$DISK"
  partprobe "$DISK"; udevadm settle
  mkfs.fat -F32 -n EFI "$ESP"
  mkfs.btrfs -f -L "$HOST" "$ROOT"

  step "Subvolumi Btrfs"
  mount "$ROOT" "$MNT"
  for p in "${SUBVOLS[@]}"; do btrfs subvolume create "$MNT/${p%%:*}"; done
  umount "$MNT"
  mount_all
}

phase_base() {
  findmnt "$MNT" >/dev/null || mount_all
  step "Installazione dei pacchetti"
  pacman -Sy --noconfirm archlinux-keyring
  pacstrap -K "$MNT" "${PACKAGES[@]}"
  # niente subvolid: dopo un rollback l'id del subvolume cambia, il nome no
  genfstab -U "$MNT" | sed -E 's/subvolid=[0-9]+,//' > "$MNT/etc/fstab"
  cat "$MNT/etc/fstab"
}

phase_config() {
  step "Lingua, fuso orario, nome"
  ln -sf "/usr/share/zoneinfo/$TZ_NAME" "$MNT/etc/localtime"
  in_chroot "hwclock --systohc --utc"
  sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' "$MNT/etc/locale.gen"
  in_chroot "locale-gen"
  echo "LANG=en_US.UTF-8" > "$MNT/etc/locale.conf"
  printf 'KEYMAP=it\nFONT=ter-124b\n' > "$MNT/etc/vconsole.conf"
  echo "$HOST" > "$MNT/etc/hostname"

  step "Utente $AGENT (sudo senza password, accesso solo con chiave)"
  in_chroot "id $AGENT >/dev/null 2>&1 || useradd -m -G wheel -s /bin/bash $AGENT"
  install -d -m 700 "$MNT/home/$AGENT/.ssh"
  install -m 600 /root/.ssh/authorized_keys "$MNT/home/$AGENT/.ssh/authorized_keys"
  in_chroot "chown -R $AGENT:$AGENT /home/$AGENT/.ssh"
  printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' "$AGENT" > "$MNT/etc/sudoers.d/10-agent"
  chmod 440 "$MNT/etc/sudoers.d/10-agent"
  in_chroot "visudo -cf /etc/sudoers.d/10-agent"
  in_chroot "passwd -l root"
  # Accesso root con chiave solo come riserva per il primo avvio: si toglie dopo aver verificato "agent"
  install -d -m 700 "$MNT/root/.ssh"
  install -m 600 /root/.ssh/authorized_keys "$MNT/root/.ssh/authorized_keys"

  step "SSH"
  cat > "$MNT/etc/ssh/sshd_config.d/10-agentdeck.conf" <<EOF
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
AllowUsers $AGENT root
EOF
  in_chroot "ssh-keygen -A && sshd -t"

  step "Rete: iwd + systemd-networkd + resolved con mDNS"
  cat > "$MNT/etc/systemd/network/20-wired.network" <<'EOF'
[Match]
Type=ether

[Network]
DHCP=yes
MulticastDNS=yes

[DHCPv4]
RouteMetric=100
EOF
  cat > "$MNT/etc/systemd/network/25-wireless.network" <<'EOF'
[Match]
Type=wlan

[Network]
DHCP=yes
MulticastDNS=yes
IgnoreCarrierLoss=3s

[DHCPv4]
RouteMetric=600
EOF
  install -d "$MNT/etc/systemd/resolved.conf.d"
  printf '[Resolve]\nMulticastDNS=yes\n' > "$MNT/etc/systemd/resolved.conf.d/mdns.conf"
  install -d -m 700 "$MNT/var/lib/iwd"
  cp -a /var/lib/iwd/*.psk "$MNT/var/lib/iwd/"

  step "zram e niente sospensione"
  printf '[zram0]\nzram-size = ram / 2\ncompression-algorithm = zstd\n' > "$MNT/etc/systemd/zram-generator.conf"
  in_chroot "systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target"

  in_chroot "systemctl enable systemd-networkd systemd-resolved iwd sshd systemd-timesyncd"
}

phase_boot() {
  step "initramfs con hook per avviare gli snapshot in sola lettura"
  [[ -f $MNT/usr/lib/initcpio/hooks/grub-btrfs-overlayfs ]] || die "hook grub-btrfs-overlayfs non trovato"
  # initramfs classico (udev): il hook overlayfs di grub-btrfs non funziona con quello basato su systemd
  install -d "$MNT/etc/mkinitcpio.conf.d"
  echo 'HOOKS=(base udev autodetect modconf kms keyboard keymap consolefont block filesystems fsck grub-btrfs-overlayfs)' \
    > "$MNT/etc/mkinitcpio.conf.d/10-agentdeck.conf"
  in_chroot "mkinitcpio -P"

  step "GRUB"
  sed -i -E 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=2/; s/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT="loglevel=3"/' \
    "$MNT/etc/default/grub"
  # con più kernel GRUB ordina i nomi dei file e sceglierebbe linux-lts come "il più recente"
  echo 'GRUB_TOP_LEVEL="/boot/vmlinuz-linux"' >> "$MNT/etc/default/grub"
  in_chroot "grub-install --target=x86_64-efi --efi-directory=/efi --bootloader-id=GRUB"
  # copia anche nel percorso di riserva \EFI\BOOT\BOOTX64.EFI, nel caso il firmware perda la voce di avvio
  in_chroot "grub-install --target=x86_64-efi --efi-directory=/efi --removable"

  step "Snapper: snapshot automatici e a orario"
  umount "$MNT/.snapshots"
  rmdir "$MNT/.snapshots"
  in_chroot "snapper --no-dbus -c root create-config /"
  in_chroot "btrfs subvolume delete /.snapshots"
  mkdir "$MNT/.snapshots"
  mount -o "$BTRFS_OPTS,subvol=@snapshots" "$ROOT" "$MNT/.snapshots"
  chmod 750 "$MNT/.snapshots"
  sed -i -E 's/^TIMELINE_LIMIT_HOURLY=.*/TIMELINE_LIMIT_HOURLY="5"/;
             s/^TIMELINE_LIMIT_DAILY=.*/TIMELINE_LIMIT_DAILY="7"/;
             s/^TIMELINE_LIMIT_(WEEKLY|MONTHLY|YEARLY)=.*/TIMELINE_LIMIT_\1="0"/;
             s/^NUMBER_LIMIT=.*/NUMBER_LIMIT="20"/' "$MNT/etc/snapper/configs/root"
  in_chroot "systemctl enable snapper-timeline.timer snapper-cleanup.timer grub-btrfsd.service"
  in_chroot "snapper --no-dbus -c root create -d 'installazione base'"
  in_chroot "grub-mkconfig -o /boot/grub/grub.cfg"

  step "Ordine di avvio UEFI: via la voce di Windows"
  local n
  for n in $(efibootmgr | sed -nE 's/^Boot([0-9A-F]{4})\* Windows Boot Manager.*/\1/p'); do efibootmgr -q -b "$n" -B; done
  efibootmgr
}

phase_verify() {
  step "Verifiche"
  cat "$MNT/etc/fstab"
  grep -E "^(menuentry|submenu)" "$MNT/boot/grub/grub.cfg" | sed 's/ --class.*//'
  ls "$MNT/boot"
  in_chroot "sshd -t && echo 'sshd: configurazione OK'"
  in_chroot "visudo -c"
  ls -la "$MNT/home/$AGENT/.ssh" "$MNT/var/lib/iwd"
  in_chroot "systemctl is-enabled systemd-networkd systemd-resolved iwd sshd systemd-timesyncd grub-btrfsd snapper-timeline.timer snapper-cleanup.timer"
  in_chroot "snapper --no-dbus -c root list"
  efibootmgr
}

phase_finish() {
  step "Chiusura"
  # dopo l'ultimo arch-chroot, che monta temporaneamente il resolv.conf del sistema live
  ln -sf ../run/systemd/resolve/stub-resolv.conf "$MNT/etc/resolv.conf"
  sync
  umount -R "$MNT"
  echo "Pronto per il riavvio."
}

case ${1:-} in
  check|disk|base|config|boot|verify|finish) "phase_$1" ;;
  *) die "uso: $0 check|disk|base|config|boot|verify|finish" ;;
esac
