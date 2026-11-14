#!/bin/bash
# Backup of sysmon reports with 7-day rotation
mkdir -p /backup
tar -czf /backup/sysmon_$(date +%F_%H%M).tar.gz /var/log/sysmon
find /backup -name "sysmon_*.tar.gz" -mtime +7 -delete
echo "$(date '+%F %T') [INFO] Backup completed" | tee -a /var/log/sysmon/backup.log
