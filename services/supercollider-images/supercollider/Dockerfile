FROM fedora:38
ARG VERSION=Version-3.13.0

RUN dnf install -q -y pipewire git cmake gcc-c++ pipewire-jack-audio-connection-kit-devel fftw-devel libsndfile-devel avahi-devel readline-devel libatomic curl nc && \
    rm -rf /var/cache/dnf

# Despite the files being present, the cmake script fails to find them without this
RUN ln -s /usr/lib64/pipewire-0.3/jack/libjack.* /usr/lib64

WORKDIR temp

# Latest release is on main branch
# Build with fewer features for a smaller install
RUN git clone --branch $VERSION --recursive --depth=1 --shallow-submodules https://github.com/supercollider/supercollider.git && \
    cd supercollider && \
    cmake -DCMAKE_BUILD_TYPE="Release" -DBUILD_TESTING=OFF -DENABLE_TESTSUITE=OFF -DSUPERNOVA=ON -DNATIVE=OFF -DNO_X11=ON -DSC_EL=OFF -DSC_VIM=OFF -DSC_QT=OFF -DSC_HIDAPI=OFF -DSC_IDE=OFF -DSC_ED=OFF -DINSTALL_HELP=OFF && \
    make -j $(nproc) && \
    make install && \
    rm -rf /temp

EXPOSE 57110:57110/udp

WORKDIR /tmp/sc

RUN useradd -G audio sclang

WORKDIR /tmp/sc

COPY ./entrypoint /run/
RUN chmod +x /run/entrypoint && \
    chown sclang:audio /run/entrypoint && \
    chown -R sclang:audio /tmp/sc

USER sclang

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:57110/health || exit 1

ENTRYPOINT ["/run/entrypoint"]
