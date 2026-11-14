#!/bin/bash
# System Health Monitoring Script - TUXNOVA
CPU_WARN=85; MEM_WARN=85; DISK_WARN=90
SERVICES="ssh cron"
LOG_DIR=/var/log/sysmon
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/health_$(date +%F).log"
ALERT=0

log(){ echo "$(date '+%F %T') [$1] $2" | tee -a "$LOG"; }
check(){ if [ "$2" -ge "$3" ]; then log CRIT "$1 at $2% (limit $3%)"; ALERT=1
         else log INFO "$1 at $2%"; fi; }

cpu=$(vmstat 1 2 | tail -1 | awk '{print 100-$15}')
mem=$(free | awk '/Mem:/ {printf "%d", $3/$2*100}')
disk=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')

log INFO "===== Health check on $(hostname) ====="
check CPU  "$cpu"  $CPU_WARN
check MEM  "$mem"  $MEM_WARN
check DISK "$disk" $DISK_WARN
log INFO "Uptime: $(uptime -p)"

for svc in $SERVICES; do
  systemctl is-active --quiet "$svc" && log INFO "$svc running" \
    || { log CRIT "$svc is DOWN"; ALERT=1; }
done

curl -sI --max-time 3 https://ubuntu.com >/dev/null 2>&1 && log INFO "Network OK" \
  || log WARN "Network unreachable"

if [ $ALERT -eq 1 ] && command -v mail >/dev/null; then
  tail -n 15 "$LOG" | mail -s "ALERT: health issue on $(hostname)" root
fi
exit $ALERT
