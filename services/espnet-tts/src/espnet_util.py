import logging
import torch
import time
from espnet_model_zoo.downloader import ModelDownloader
from espnet2.bin.tts_inference import Text2Speech
from functools import reduce, lru_cache
from os import environ
from parallel_wavegan.utils import download_pretrained_model
from parallel_wavegan.utils import load_model

fs = 22050
tag = "kan-bayashi/ljspeech_conformer_fastspeech2"
vocoder_tag = "ljspeech_parallel_wavegan.v1"

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
        wav = vocoder.inference(c)
    rtf = (time.time() - start) / (len(wav) / fs)
    logger.info(f"RTF: {rtf}")
    return wav.view(-1).cpu().numpy()
