import os
import torch
import importlib
import torch.nn as nn

from config import system_configs
from models.py_utils.data_parallel import DataParallel

torch.manual_seed(317)

class Network(nn.Module):
    def __init__(self, model, loss):
        super(Network, self).__init__()

        self.model = model
        self.loss  = loss

    def forward(self, xs, ys, **kwargs):
        preds = self.model(*xs, **kwargs)
        loss  = self.loss(preds, ys, **kwargs)
        return loss

# for model backward compatibility
# previously model was wrapped by DataParallel module
class DummyModule(nn.Module):
    def __init__(self, model):
        super(DummyModule, self).__init__()
        self.module = model

    def forward(self, *xs, **kwargs):
        return self.module(*xs, **kwargs)

class NetworkFactory(object):
    def __init__(self, db):
        super(NetworkFactory, self).__init__()

        module_file = "models.{}".format(system_configs.snapshot_name)
        nnet_module = importlib.import_module(module_file)

        self.model   = DummyModule(nnet_module.model(db))
        self.loss    = nnet_module.loss
        self.network = Network(self.model, self.loss)

        total_params = 0
        for params in self.model.parameters():
            num_params = 1
            for x in params.size():
                num_params *= x
            total_params += num_params

        if system_configs.opt_algo == "adam":
            self.optimizer = torch.optim.Adam(
                filter(lambda p: p.requires_grad, self.model.parameters())
            )
        elif system_configs.opt_algo == "sgd":
            self.optimizer = torch.optim.SGD(
                filter(lambda p: p.requires_grad, self.model.parameters()),
                lr=system_configs.learning_rate, 
                momentum=0.9, weight_decay=0.0001
            )
        else:
            raise ValueError("unknown optimizer")

    def cuda(self, cuda_id):
        if (cuda_id >= 0):
            self.model.cuda(cuda_id)
            self.network.cuda(cuda_id)
        self.cuda_id = cuda_id

    def cpu(self):
        self.model.cpu()
        self.network.cpu()

    def train_mode(self):
        self.network.train()

    def eval_mode(self):
        self.network.eval()

    def train(self, xs, ys, **kwargs):
        xs = [x.cuda(non_blocking=True, device=self.cuda_id) for x in xs]
        ys = [y.cuda(non_blocking=True, device=self.cuda_id) for y in ys]
        self.optimizer.zero_grad()
        loss = self.network(xs, ys)
        loss = loss.mean()
        loss.backward()
        self.optimizer.step()
        return loss

    def validate(self, xs, ys, **kwargs):
        with torch.no_grad():
            if torch.cuda.is_available():
                xs = [x.cuda(non_blocking=True, device=self.cuda_id) for x in xs]
                ys = [y.cuda(non_blocking=True, device=self.cuda_id) for y in ys]

            loss = self.network(xs, ys)
            loss = loss.mean()
            return loss

    def test(self, xs, cuda_id=0, **kwargs):
        with torch.no_grad():
            if (torch.cuda.is_available() and cuda_id >=0):
                xs = [x.cuda(non_blocking=True, device=self.cuda_id) for x in xs]
            return self.model(*xs, **kwargs)

    def set_lr(self, lr):
        for param_group in self.optimizer.param_groups:
            param_group["lr"] = lr

    def load_pretrained_params(self, pretrained_model):
        with open(pretrained_model, "rb") as f:
            params = torch.load(f)
            self.model.load_state_dict(params)

    def load_params(self, iteration, num, cuda_id=0):
        cache_file = str(system_configs.snapshot_file.format(iteration))
        '''
        if num == 1:
            cache_file = 'data/clsdata(1031)/cache/nnet/CornerNetCls/CornerNetCls_50000.pth'
        if num == 4:
            cache_file = 'data/linedata(1028)/cache/nnet/CornerNetLine/CornerNetLine_50000.pth'
        if num == 5:
            cache_file = 'data/linedata(1028)/cache/nnet/CornerNetLineClsReal/CornerNetLineClsReal_20000.pth'
        '''
        print("loading model from {}".format(cache_file))
    
        if (torch.cuda.is_available() and cuda_id >= 0):
            self.model.load_state_dict(torch.load(cache_file), strict=False)
        else:
            self.model.load_state_dict(torch.load(cache_file, map_location='cpu'), strict=False)
        

    def save_params(self, iteration):
        cache_file = system_configs.snapshot_file.format(iteration)
        with open(cache_file, "wb") as f:
            params = self.model.state_dict()
            torch.save(params, f)
