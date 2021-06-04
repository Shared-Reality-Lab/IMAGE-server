FROM alpine:latest
# Default to latest version of supercollider
ARG VERSION=develop

RUN apk add --no-cache git g++ cmake make pipewire pipewire-jack libsndfile-dev fftw-dev jack-dev avahi-dev readline-dev linux-headers

# Despite the files being present, the cmake script fails to find them without this
RUN ln -sf /usr/lib/pipewire-0.3/jack/libjack.* /usr/lib

WORKDIR temp

# Latest release is on main branch
# Build with fewer features for a smaller install
RUN git clone --depth=1 --shallow-submodules --branch $VERSION --recursive https://github.com/supercollider/supercollider.git && \
    cd supercollider && \
    cmake -DCMAKE_BUILD_TYPE="Release" -DBUILD_TESTING=OFF -DENABLE_TESTSUITE=OFF -DSUPERNOVA=OFF -DNATIVE=OFF -DNO_X11=ON -DSC_EL=OFF -DSC_VIM=OFF -DSC_QT=OFF -DSC_HIDAPI=OFF -DSC_IDE=OFF -DSC_ED=OFF -DSC_ABLETON_LINK=OFF -DINSTALL_HELP=OFF && \
    make -j $(nproc) && \
    make install && \
    rm -rf /temp

EXPOSE 57110:57110/udp

RUN adduser --system sclang audio

WORKDIR /tmp/sc

COPY ./entrypoint /run/
RUN chmod +x /run/entrypoint && \
    chown sclang:audio /run/entrypoint && \
    chown -R sclang:audio /tmp/sc

USER sclang

ENTRYPOINT ["/run/entrypoint"]
