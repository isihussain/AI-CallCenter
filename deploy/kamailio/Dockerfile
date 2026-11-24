FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates kamailio kamailio-tls-modules \
    && rm -rf /var/lib/apt/lists/*
EXPOSE 5061/tcp 5070/udp
CMD ["kamailio", "-DD", "-E", "-P", "/run/kamailio.pid", "-f", "/etc/kamailio/oim.cfg"]
