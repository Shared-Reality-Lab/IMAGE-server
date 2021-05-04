FROM supercollider:alpine
ARG VERSION=Version-3.11.1

# Install sc3-plugins

USER root

WORKDIR /temp
RUN git clone --depth=1 --shallow-submodules --recursive --branch $VERSION https://github.com/supercollider/sc3-plugins.git && \
    cd sc3-plugins && \
    cmake -DCMAKE_BUILD_TYPE="Release" -DSUPERNOVA=OFF -DLADSPA=ON && \
    make && \
    make install && \
    rm -rf /temp

USER sclang
WORKDIR /tmp/sc

COPY quarks_install.scd /tmp/sc/quarks_install.scd

RUN sclang quarks_install.scd
RUN rm quarks_install.scd
    
ENTRYPOINT ["/run/entrypoint"]
