FROM supercollider-extra:3.11.1

USER root

# This is arbitrary
RUN groupadd -g 4322 storage
RUN usermod -a -G storage sclang

WORKDIR /tmp/sc-store
RUN chown sclang:storage /tmp/sc-store
RUN chmod 2774 /tmp/sc-store

WORKDIR /tmp/sc
COPY --chown=sclang:audio example.scd ./

USER sclang
