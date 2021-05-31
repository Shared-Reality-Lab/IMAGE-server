from espnet_model_zoo.downloader import ModelDownloader
from parallel_wavegan.utils import download_pretrained_model

d = ModelDownloader()
d.download_and_unpack("kan-bayashi/ljspeech_conformer_fastspeech2")
download_pretrained_model("ljspeech_parallel_wavegan.v1")
