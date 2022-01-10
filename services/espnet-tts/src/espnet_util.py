# Copyright (c) 2021 IMAGE Project, Shared Reality Lab, McGill University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# and our Additional Terms along with this program.
# If not, see
# <https://github.com/Shared-Reality-Lab/IMAGE-server/LICENSE>.

import logging
import torch
import time
from espnet_model_zoo.downloader import ModelDownloader
from espnet2.bin.tts_inference import Text2Speech
from functools import lru_cache
from os import environ
from parallel_wavegan.utils import download_pretrained_model
from parallel_wavegan.utils import load_model

fs = 22050
tag = "kan-bayashi/ljspeech_conformer_fastspeech2"
# vocoder_tag = "ljspeech_parallel_wavegan.v3"
vocoder_tag = "ljspeech_full_band_melgan.v2"

logging.basicConfig(format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

d = ModelDownloader()
device = environ["TORCH_DEVICE"]
logger.info(f"Device: {device}")
text2speech = Text2Speech(
    **d.download_and_unpack(tag),
    device=device,
    threshold=0.5,
    minlenratio=0.0,
    maxlenratio=10.0,
    use_att_constraint=False,
    backward_window=1,
    forward_window=3,
    # Only for FastSpeech & FastSpeech2
    speed_control_alpha=1.0,
)
text2speech.spc2wav = None
vocoder = load_model(download_pretrained_model(vocoder_tag)).to(device).eval()
vocoder.remove_weight_norm()


@lru_cache
def tts(text):
    with torch.no_grad():
        start = time.time()
        wav, c, *_ = text2speech(text)
        t2 = time.time()
        wav = vocoder.inference(c)
        t3 = time.time()
    rtf = (t3 - start) / (len(wav) / fs)
    logger.info(f"RTF: {rtf}")
    logger.info(f"Elapsed text2speech: {t2 - start}")
    logger.info(f"Elapsed vocoder: {t3 - t2}")
    return wav.view(-1).cpu().numpy()
