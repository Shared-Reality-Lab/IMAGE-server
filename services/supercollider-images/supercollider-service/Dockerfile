FROM ghcr.io/shared-reality-lab/supercollider:extra-3.11.1
LABEL "org.opencontainers.image.title"="SuperCollider IMAGE Service" \
      "org.opencontainers.image.description"="A SuperCollider Service for IMAGE" \
      "org.opencontainers.image.authors"="IMAGE Project <image@cim.mcgill.ca>" \
      "org.opencontainers.image.licenses"="AGPL-3.0-or-later"

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
