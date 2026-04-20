#!/usr/bin/env bash
set -euo pipefail

CHAIN="DOCKER-USER"

iptables -N "$CHAIN" 2>/dev/null || true
iptables -C "$CHAIN" -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN 2>/dev/null || \
  iptables -I "$CHAIN" 1 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN

for rule in \
  "-i lo -j RETURN" \
  "-s 10.0.0.0/8 -j RETURN" \
  "-s 172.16.0.0/12 -j RETURN" \
  "-s 192.168.0.0/16 -j RETURN"
do
  iptables -C "$CHAIN" $rule 2>/dev/null || iptables -I "$CHAIN" 2 $rule
done

for port in 3306 5432 5678 6379 8222; do
  iptables -C "$CHAIN" -p tcp --dport "$port" -j DROP 2>/dev/null || \
    iptables -I "$CHAIN" 5 -p tcp --dport "$port" -j DROP
done

iptables -C "$CHAIN" -j RETURN 2>/dev/null || iptables -A "$CHAIN" -j RETURN
