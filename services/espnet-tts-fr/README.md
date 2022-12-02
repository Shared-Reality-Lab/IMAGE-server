# ESPnet French TTS Service

![license: AGPL](https://img.shields.io/badge/license-AGPL-success) [GitHub Container Registry Package](https://github.com/Shared-Reality-Lab/IMAGE-server/pkgs/container/image-service-espnet-tts-fr)

## Overview

This is a container that performs text-to-speech for IMAGE using the [ESPnet](https://github.com/espnet/espnet) platform.
As of the time of writing (2022-12-02), a Tacotron model trained on the SIWIS dataset for 300 epochs and the [parallel_wavegan](https://pypi.org/project/parallel-wavegan/) `ljspeech_full_band_melgan.v2` model are used.
All audio files are returned in the WAVE format.
This container runs on port 80.

## Options

- `TORCH_DEVICE`: Controls the device used by pytorch. By default, this is set to "cpu" but can be changed to "cuda" if an NVIDIA GPU is available.

## Endpoints

### Simple

Available at `POST /service/tts/simple` where the body is a JSON object with the key `text` set to the string to TTS.

### Segments

Available at `POST /server/tts/segments` where the body is a JSON object with the key `segments` set to an array of strings.
All the text will be TTSed and put into a single WAV file.
The result will be a JSON object where the field `audio` contains the data URL of the audio file.
To allow each segment of text to be located separately, a separate field called `durations` is an array of the duration of each segment
in the order they were sent in the request given in number of samples.

For example, to locate the TTS of the third text segment, it would be in the audio file from sample `d1 + d2` to sample `d1 + d2 + d3`.
