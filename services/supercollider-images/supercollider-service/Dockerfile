FROM ghcr.io/shared-reality-lab/supercollider:extra-3.11.1

USER root

# This is arbitrary
RUN groupadd -g 4322 storage
RUN usermod -a -G storage sclang

WORKDIR /tmp/sc-store
RUN chown sclang:storage /tmp/sc-store
RUN chmod 2774 /tmp/sc-store

WORKDIR /tmp/sc
COPY --chown=sclang:audio *.scd ./
COPY --chown=sclang:audio ./IMAGE ./IMAGE

USER sclang
RUN printf 'Quarks.install("/tmp/sc/IMAGE");' | sclang
