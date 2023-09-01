import torch
import logging


class Classifier(torch.nn.Module):
    def __init__(self):
        super(Classifier, self).__init__()
        self.dinov2 = torch.hub.load(
            'facebookresearch/dinov2', 'dinov2_vits14')
        # freeze layers
        for param in self.dinov2.parameters():
            param.requires_grad = False
        self.dinov2.head = torch.nn.Linear(in_features=384, out_features=25)

    def forward(self, x):
        x = self.dinov2(x)
        return x


labels = ['baby_crawling',
          'blowing_candles',
          'brushing_teeth',
          'clapping',
          'climbing',
          'drinking',
          'eating',
          'fighting',
          'fishing',
          'gardening',
          'jumping',
          'lunging',
          'playing_instrument',
          'doing_push_ups',
          'reading',
          'riding_bike',
          'riding_horse',
          'running',
          'shaving_beard',
          'sitting',
          'sleeping',
          'taking_photos',
          'walking',
          'watching_tv',
          'writing_on_board']


def detect(img, id, conf_thres, model):
    logging.info("Person detected")

    if img.ndim == 3:
        img = torch.unsqueeze(img, 0)

    try:    
        img = img.to("cuda")
    except Exception as e:
        logging.error("Error while loading image on GPU: {}".format(e))
        raise e
    
    out = model(img)
    conf, pred = torch.max(out, 1)
    conf = conf.item()
    sm = torch.nn.Softmax(dim=1)
    soft = sm(out)
    conf = soft[0][pred.item()].item()

    if conf < conf_thres:
        logging.info("Confidence too low, skipping detected person")
        return None

    action_data = {
        "personID": id,
        "action": labels[pred.item()],
        "confidence": conf
    }

    logging.info("Action detected")

    return action_data
