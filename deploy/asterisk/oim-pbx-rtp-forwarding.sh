#!/bin/sh
set -eu

CONFIG_FILE=${OIM_PBX_RTP_ENV_FILE:-/etc/default/oim-pbx-rtp-forwarding}
if [ -r "$CONFIG_FILE" ]; then
    . "$CONFIG_FILE"
fi

PUBLIC_INTERFACE=${OIM_PBX_PUBLIC_INTERFACE:-eth0}
PBX_ADDRESS=${OIM_PBX_CONTAINER_IP:-172.19.0.10}
RTP_START=${OIM_PBX_RTP_START:-10000}
RTP_FINISH=${OIM_PBX_RTP_FINISH:-20000}

case "$RTP_START:$RTP_FINISH" in
    *[!0-9:]*|:*|*:) echo "Invalid RTP port range" >&2; exit 2 ;;
esac
case "$PUBLIC_INTERFACE" in
    *[!A-Za-z0-9_.:-]*) echo "Invalid public interface" >&2; exit 2 ;;
esac

PUBLIC_ADDRESS=$(ip -4 -o addr show dev "$PUBLIC_INTERFACE" scope global | awk 'NR == 1 { split($4, parts, "/"); print parts[1] }')
if [ -z "$PUBLIC_ADDRESS" ]; then
    echo "No public IPv4 address found on the configured interface" >&2
    exit 1
fi

nat_rule="-i $PUBLIC_INTERFACE -p udp -d $PUBLIC_ADDRESS --dport $RTP_START:$RTP_FINISH -j DNAT --to-destination $PBX_ADDRESS"
filter_rule="-i $PUBLIC_INTERFACE -p udp -d $PBX_ADDRESS/32 --dport $RTP_START:$RTP_FINISH -m conntrack --ctstate NEW,ESTABLISHED,RELATED -j ACCEPT"

case "${1:-}" in
    start)
        iptables -w 5 -t nat -C PREROUTING $nat_rule 2>/dev/null || iptables -w 5 -t nat -I PREROUTING 1 $nat_rule
        iptables -w 5 -C DOCKER-USER $filter_rule 2>/dev/null || iptables -w 5 -I DOCKER-USER 1 $filter_rule
        ;;
    stop)
        iptables -w 5 -C DOCKER-USER $filter_rule 2>/dev/null && iptables -w 5 -D DOCKER-USER $filter_rule || true
        iptables -w 5 -t nat -C PREROUTING $nat_rule 2>/dev/null && iptables -w 5 -t nat -D PREROUTING $nat_rule || true
        ;;
    status)
        iptables -w 5 -t nat -C PREROUTING $nat_rule && iptables -w 5 -C DOCKER-USER $filter_rule
        echo "OIM RTP forwarding is active"
        ;;
    *)
        echo "Usage: $0 {start|stop|status}" >&2
        exit 2
        ;;
esac
