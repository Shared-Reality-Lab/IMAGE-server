FROM ghcr.io/shared-reality-lab/supercollider:latest
ARG VERSION=Version-3.11.1

USER root

# Wanted by MP3
RUN dnf install -q -y lame vorbis-tools unzip which && \
    rm -rf /var/cache/dnf

# Install sc3-plugins
WORKDIR /temp
RUN git clone --depth=1 --shallow-submodules --recursive --branch $VERSION https://github.com/supercollider/sc3-plugins.git && \
    cd sc3-plugins && \
    cmake -DCMAKE_BUILD_TYPE="Release" -DSUPERNOVA=ON -DLADSPA=ON && \
    make -j $(nproc) && \
    make install && \
    rm -rf /temp

USER sclang
WORKDIR /tmp/sc

COPY quarks_install.scd /tmp/sc/quarks_install.scd
RUN sclang quarks_install.scd
RUN rm quarks_install.scd

# Remove graphics dependencies of ATK-SC3
# https://github.com/ambisonictoolkit/atk-sc3/issues/100
RUN rm -rf ~/.local/share/SuperCollider/downloaded-quarks/PointView \
    ~/.local/share/SuperCollider/downloaded-quarks/wslib/wslib-classes/GUI \
    ~/.local/share/SuperCollider/downloaded-quarks/wslib/wslib-classes/Main\ Features/Interpolation/extPen-splineCurve.sc \
    ~/.local/share/SuperCollider/downloaded-quarks/wslib/wslib-classes/Main\ Features/SVGFile/

COPY atk_install.scd /tmp/sc/atk_install.scd
RUN sclang atk_install.scd
RUN rm atk_install.scd

ENTRYPOINT ["/run/entrypoint"]
