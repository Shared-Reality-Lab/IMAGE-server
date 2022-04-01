# SuperCollider Docker Image

This is a docker image of [SuperCollider](https://supercollider.github.io/) using [Fedora linux](https://getfedora.org).
It was built for IMAGE to perform non-realtime synthesis in a containerized environment, however it could be used for other purposes.
It is worth noting that we do not connect an audio device to it and it works by detecting the dummy device in pipewire.
If using plain JACK, it would fail with no devices.
This means that, by default, you will not be able to hear audio on any output device using this image.:

The version of SuperCollider built with this is controlled using the `VERSION` argument.
We typically try to keep this updated to the latest release of SuperCollider.
If you want to change this, run
```
docker build --build-arg VERSION=[version] .
```
where `[version]` is either a branch or tag on the [SuperCollider git repository](https://github.com/supercollider/supercollider).
