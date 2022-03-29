# Highcharts Handler

![license: AGPL](https://camo.githubusercontent.com/b53b1136762ea55ee6a2d641c9f8283b8335a79b3cb95cbab5a988e678e269b8/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6c6963656e73652d4147504c2d73756363657373) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-handler-high-charts)

## What is this?

This is a [handler](https://github.com/Shared-Reality-Lab/IMAGE-server/wiki/2.-Handlers,-Preprocessors-and-Services#handlers=) component that creates a sptialized audio representation of [Highcharts](https://www.highcharts.com/) charts.
Currently, it only supports line or area charts with a single trend and pie charts.
It communicates with the [ESPnet TTS service](../../services/espnet-tts) for text-to-speech
and [SuperCollider](../../services/supercollider-service/charts) for audio synthesis.
