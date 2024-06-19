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
# If not, see <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.
#
# This was adapted from Junyu Luo's DeepRule project <https://github.com/soap117/DeepRule>

import os
import json
import torch
from scipy.signal import find_peaks
import numpy as np

import matplotlib
matplotlib.use("Agg")
import cv2
from config.config import system_configs
from models.py_factory import NetworkFactory
from db.datasets import datasets
import importlib
from post_processing.Cls import GroupCls
from post_processing.LineQuiry import GroupQuiry
from post_processing.LIneMatch import GroupLine
from post_processing.Bar import GroupBar
from post_processing.Pie import GroupPie

import math
from PIL import Image
torch.backends.cudnn.benchmark = False
import requests
import time
import re


def load_net(num, testiter, cfg_name, data_dir, cache_dir, result_dir, cuda_id):
    cfg_file = os.path.join(system_configs.config_dir, cfg_name + ".json")
    with open(cfg_file, "r") as f:
        configs = json.load(f)
    configs["system"]["snapshot_name"] = cfg_name
    configs["system"]["data_dir"] = data_dir
    configs["system"]["cache_dir"] = cache_dir
    configs["system"]["result_dir"] = result_dir
    configs["system"]["tar_data_dir"] = "Cls"
    system_configs.update_config(configs["system"])

    train_split = system_configs.train_split
    val_split = system_configs.val_split
    test_split = system_configs.test_split

    split = {
        "training": train_split,
        "validation": val_split,
        "testing": test_split
    }["validation"]

    test_iter = system_configs.max_iter if testiter is None else testiter
    dataset = system_configs.dataset
    db = datasets[dataset](configs["db"], split)
    
    nnet = NetworkFactory(db)
    nnet.load_params(test_iter, num, cuda_id=cuda_id)
    if (torch.cuda.is_available()):
        print (torch.cuda.is_available())
        nnet.cuda(cuda_id)
    nnet.eval_mode()
    return db, nnet


def pre_load_nets(num, methods):

    if (1 in num):
        db_cls, nnet_cls = load_net(1, 50000, "CornerNetCls", "data/clsdata(1031)", "data/clsdata(1031)/cache",
                                    "data/clsdata(1031)/result", 0)

        path = 'pipeline_inference.test_%s' % "CornerNetCls"
        testing_cls = importlib.import_module(path).testing
        methods['Cls'] = [db_cls, nnet_cls, testing_cls]

    if (2 in num):
        db_bar, nnet_bar = load_net(2, 50000, "CornerNetPureBar", "data/bardata(1031)", "data/bardata(1031)/cache",
                                "data/bardata(1031)/result", 0)
        path = 'pipeline_inference.test_%s' % "CornerNetPureBar"
        testing_bar = importlib.import_module(path).testing
        methods['Bar'] = [db_bar, nnet_bar, testing_bar]

    if (3 in num):
        db_pie, nnet_pie = load_net(3, 50000, "CornerNetPurePie", "data/piedata(1008)", "data/piedata(1008)/cache",
                                "data/piedata(1008)/result", 0)
        path = 'pipeline_inference.test_%s' % "CornerNetPurePie"
        testing_pie = importlib.import_module(path).testing
        methods['Pie'] = [db_pie, nnet_pie, testing_pie]
    
    if (4 in num):
        db_line, nnet_line = load_net(4, 50000, "CornerNetLine", "data/linedata(1028)", "data/linedata(1028)/cache",
                                    "data/linedata(1028)/result", 0)
        path = 'pipeline_inference.test_%s' % "CornerNetLine"
        testing_line = importlib.import_module(path).testing
        methods['Line'] = [db_line, nnet_line, testing_line]

    if (5 in num):
        db_line_cls, nnet_line_cls = load_net(5, 20000, "CornerNetLineClsReal", "data/linedata(1028)",
                                            "data/linedata(1028)/cache",
                                            "data/linedata(1028)/result", 0)
        path = 'pipeline_inference.test_%s' % "CornerNetLineCls"
        testing_line_cls = importlib.import_module(path).testing
        methods['LineCls'] = [db_line_cls, nnet_line_cls, testing_line_cls]

    return methods


def ocr_result(image_path):
    api_key = os.environ["CHART_KEY"]
    subscription_key = api_key
    vision_base_url = "https://canadacentral.api.cognitive.microsoft.com/vision/v2.0/"
    ocr_url = vision_base_url + "read/core/asyncBatchAnalyze"
    headers = {'Ocp-Apim-Subscription-Key': subscription_key, 'Content-Type': 'application/octet-stream'}
    params = {'language': 'unk', 'detectOrientation': 'true'}
    image_data = open(image_path, "rb").read()
    response = requests.post(ocr_url, headers=headers, params=params, data=image_data)
    response.raise_for_status()
    op_location = response.headers['Operation-Location']
    analysis = {}
    while "recognitionResults" not in analysis.keys():
        time.sleep(3)
        binary_content = requests.get(op_location, headers=headers, params=params).content
        analysis = json.loads(binary_content.decode('ascii'))
    line_infos = [region["lines"] for region in analysis["recognitionResults"]]
    word_infos = []
    for line in line_infos:
        for word_metadata in line:
            for word_info in word_metadata["words"]:
                word_infos.append(word_info)
    return word_infos

def check_intersection(box1, box2):
    if (box1[2] - box1[0]) + ((box2[2] - box2[0])) > max(box2[2], box1[2]) - min(box2[0], box1[0]) \
            and (box1[3] - box1[1]) + ((box2[3] - box2[1])) > max(box2[3], box1[3]) - min(box2[1], box1[1]):
        Xc1 = max(box1[0], box2[0])
        Yc1 = max(box1[1], box2[1])
        Xc2 = min(box1[2], box2[2])
        Yc2 = min(box1[3], box2[3])
        intersection_area = (Xc2-Xc1)*(Yc2-Yc1)
        return intersection_area/((box2[3]-box2[1])*(box2[2]-box2[0]))
    else:
        return 0

def try_math(image_path, cls_info):
    title_list = [1, 2, 3]
    title2string = {}
    max_value = 1
    min_value = 0
    max_y = 0
    min_y = 1
    word_infos = ocr_result(image_path)
    for id in title_list:
        if id in cls_info.keys():
            predicted_box = cls_info[id]
            words = []
            for word_info in word_infos:
                word_bbox = [word_info["boundingBox"][0], word_info["boundingBox"][1], word_info["boundingBox"][4], word_info["boundingBox"][5]]
                if check_intersection(predicted_box, word_bbox) > 0.5:
                    words.append([word_info["text"], word_bbox[0], word_bbox[1]])
            words.sort(key=lambda x: x[1]+10*x[2])
            word_string = ""
            for word in words:
                word_string = word_string + word[0] + ' '
            title2string[id] = word_string
    if 5 in cls_info.keys():
        plot_area = cls_info[5]
        y_max = plot_area[1]
        y_min = plot_area[3]
        x_board = plot_area[0]
        dis_max = 10000000000000000
        dis_min = 10000000000000000
        for word_info in word_infos:
            word_bbox = [word_info["boundingBox"][0], word_info["boundingBox"][1], word_info["boundingBox"][4], word_info["boundingBox"][5]]
            word_text = word_info["text"]
            word_text = re.sub('[^-+0123456789.]', '',  word_text)
            word_text_num = re.sub('[^0123456789]', '', word_text)
            word_text_pure = re.sub('[^0123456789.]', '', word_text)
            if len(word_text_num) > 0 and word_bbox[2] <= x_board+10:
                dis2max = math.sqrt(math.pow((word_bbox[0]+word_bbox[2])/2-x_board, 2)+math.pow((word_bbox[1]+word_bbox[3])/2-y_max, 2))
                dis2min = math.sqrt(math.pow((word_bbox[0] + word_bbox[2]) / 2 - x_board, 2) + math.pow(
                    (word_bbox[1] + word_bbox[3]) / 2 - y_min, 2))
                y_mid = (word_bbox[1]+word_bbox[3])/2
                if dis2max <= dis_max:
                    dis_max = dis2max
                    max_y = y_mid
                    max_value = float(word_text_pure)
                    if word_text[0] == '-':
                        max_value = -max_value
                if dis2min <= dis_min:
                    dis_min = dis2min
                    min_y = y_mid
                    min_value = float(word_text_pure)
                    if word_text[0] == '-':
                        min_value = -min_value
                        
        delta_min_max = max_value-min_value
        delta_mark = min_y - max_y
        delta_plot_y = y_min - y_max
        delta = delta_min_max/delta_mark
        if abs(min_y-y_min)/delta_plot_y > 0.1:
            min_value = int(min_value + (min_y-y_min)*delta)

    return title2string, round(min_value, 2), round(max_value, 2), word_infos


def findXlabels(word_infos, plot_area):

    y_list = []
    x_list = []
    for word_info in word_infos:
        y_list.append(word_info['boundingBox'][1])
        x_list.append((word_info['boundingBox'][0] + word_info['boundingBox'][2])*0.5)
    
    y = np.asarray(y_list)
    y_approx = list(np.around(y/5)*5)

    y_filtered = []
    words_filtered = []
    xlist_filtered = []

    for i in range (0, len(y_approx)):
        if ((y_approx[i] + 5) > plot_area[3]):
            y_filtered.append(y_approx[i])
            words_filtered.append(word_infos[i])
            xlist_filtered.append(x_list[i])

    min_value = min(y_filtered)
    idx = [index for index, value in enumerate(y_filtered) if value == min_value]
    
    if (max(xlist_filtered) - min (xlist_filtered) < 0.5*(abs(plot_area[2] - plot_area[0]))):
        for i in idx:
            y_filtered[i] = max(y_filtered)
        min_value = min(y_filtered)
        idx = [index for index, value in enumerate(y_filtered) if value == min_value]

    x_labels = []
    x_pos = []            
    for i in idx:
        x_labels.append(words_filtered[i])
        x_pos.append(xlist_filtered[i])

    return x_labels, x_pos


def groupByLabels(line_data, x_pos, plot_area):
    x_rel, _ = zip(*line_data)
    x = plot_area[0] + np.asarray(x_rel)*(plot_area[2] - plot_area[0])

    for i in range (0, len(x)):     # for each point in x
        min = 1000000000

        for j in range (0, len(x_pos)):    # check dist with every point in x_pos and find min
            if abs(x[i] - x_pos[j]) < min:
                min = abs(x[i] - x_pos[j])
                min_idx = j

        line_data[i].append(min_idx)

    return line_data


def group_bars_by_labels(pixel_points, x_pos):
    
    for i in range(0, len(pixel_points)):
        x = 0.5*(pixel_points[i][0] + pixel_points[i][2])
        min = 10000000000

        for j in range (0, len(x_pos)):
            if abs(x - x_pos[j]) < min:
                min = abs(x - x_pos[j])
                min_idx = j

        pixel_points[i].append(min_idx)

    return pixel_points


def test(image_path, methods, args, suffix=None, min_value_official=None, max_value_official=None):
    image_cls = Image.open(image_path)
    image = cv2.imread(image_path)
    with torch.no_grad():

        results = methods['Cls'][2](image, methods['Cls'][0], methods['Cls'][1], cuda_id=0, debug=False)

        info, tls, brs = results[0], results[1], results[2]

        image_painted, cls_info = GroupCls(image_cls, tls, brs)
        title2string, min_value, max_value, word_infos = try_math(image_path, cls_info)
        
        plot_area = cls_info[5][0:4]
        if info['data_type'] != 2:
            x_labels, x_pos = findXlabels(word_infos, plot_area)
        else:
            x_labels = x_pos = []
        
        chartinfo = [info['data_type'], cls_info, title2string, min_value, max_value]
        chartinfo.append(x_labels)

        # -------------------------------------------------
        methods['Cls'][1].cpu()
        if args.empty_cache:
            torch.cuda.empty_cache()
        # -------------------------------------------------

        # Bar chart
        if info['data_type'] == 0:

            # ---------------------------------------------
            if args.mode == 1:
                methods = pre_load_nets([2], methods)
            if args.mode == 2:
                methods['Bar'][1].cuda(0)
            # ---------------------------------------------

            results = methods['Bar'][2](image, methods['Bar'][0], methods['Bar'][1], debug=False)
            tls = results[0]
            brs = results[1]
            image_painted, bar_data, pixel_points = GroupBar(image_painted, tls, brs, plot_area, min_value, max_value)

            pixel_points = group_bars_by_labels(pixel_points, x_pos)

            return plot_area, image_painted, bar_data, chartinfo, x_labels, pixel_points, info['data_type'], image.shape

        # Line chart
        if info['data_type'] == 1:

            # ---------------------------------------------
            if args.mode == 1:
                methods = pre_load_nets([4], methods)
            if args.mode == 2:
                methods['Line'][1].cuda(0)
            # ---------------------------------------------

            results = methods['Line'][2](image, methods['Line'][0], methods['Line'][1], cuda_id=0, debug=False)
            keys = results[0]
            hybrids = results[1]
            image_painted, quiry, keys, hybrids = GroupQuiry(image_painted, keys, hybrids, plot_area, min_value, max_value)

            # ---------------------------------------------
            if args.mode == 1:
                del methods['Line']
                methods = pre_load_nets([5], methods)
            if args.mode == 2:
                methods['LineCls'][1].cuda(0)
                methods['Line'][1].cpu()
            # ---------------------------------------------

            results = methods['LineCls'][2](image, methods['LineCls'][0], quiry, methods['LineCls'][1], cuda_id=0, debug=False)
            line_data, pixel_points = GroupLine(image_painted, keys, hybrids, plot_area, results, min_value, max_value)
            
            grouped_data = groupByLabels(line_data[0], x_pos, plot_area)

            return plot_area, image_painted, grouped_data, chartinfo, x_labels, pixel_points[0], info['data_type'], image.shape

        # Pie chart
        if info['data_type'] == 2:

            # ---------------------------------------------
            if args.mode == 1:
                methods = pre_load_nets([3], methods)
            if args.mode == 2:
                methods['Pie'][1].cuda(0)
            # ---------------------------------------------

            results = methods['Pie'][2](image, methods['Pie'][0], methods['Pie'][1], debug=False)
            cens = results[0]
            keys = results[1]
            image_painted, pie_data, groups = GroupPie(image_painted, cens, keys)
            
            return plot_area, image_painted, pie_data, chartinfo, x_labels, groups, info['data_type'], image.shape            


def findPeaksDips(line_data):
    _, yp, _ = zip(*line_data)
    
    yd = []
    maximum = max(yp)
    for value in yp:
        yd.append(maximum - value)

    peaks, _ = find_peaks(yp, prominence=10000)
    dips, _ = find_peaks(yd, prominence=10000)
    
    return peaks, dips



def get_data_from_chart(img, methods, args):

    if max(img.shape[0], img.shape[1]) > 950:
        
        scale_percent = 900/(max(img.shape[0], img.shape[1]))
        width = int(img.shape[1] * scale_percent)
        height = int(img.shape[0] * scale_percent)
        dim = (width, height)
        
        img = cv2.resize(img, dim)

    cv2.imwrite('./input.png', img)
    image_path = './input.png'
    plot_area, image_painted, data, chartinfo, x_labels, pixel_points, type_no, d = test(image_path, methods, args)

    if type_no == 0:
        chart_type = 'Bar Chart'
    if type_no == 1:
        chart_type = 'Line Chart'
    if type_no == 2:
        chart_type = 'Pie Chart'

    if(len(chartinfo[2])==0):
        title = "not available"
    else:
        try:
            title = chartinfo[2][2]
        except IndexError:
            title = None

    if (type_no == 0):
    
        bars = []
        for i in range (0, len(pixel_points)):
            if (len(pixel_points[i]) != 5):
                print ("ERRORRR!!!!")
            
            else:    
                y = pixel_points[i][3] - pixel_points[i][1]
                frac_y = (y) / (plot_area[3] - plot_area[1])
                value = (chartinfo[4] - chartinfo[3]) * frac_y + chartinfo[3]

                pixel_points[i][0] /= d[1]
                pixel_points[i][1] /= d[0]
                pixel_points[i][2] /= d[1]
                pixel_points[i][3] /= d[0]

                temp = {
                    "ID": i + 1,
                    "value": value,
                    "x_label": x_labels[pixel_points[i][4]]['text'],
                    "coords": pixel_points[i][:4],
                    "centroid": [0.5*(pixel_points[i][0] + pixel_points[i][2]), 0.5*(pixel_points[i][1] + pixel_points[i][3])],
                    "area": (pixel_points[i][2] - pixel_points[i][0])*(pixel_points[i][3] - pixel_points[i][1])
                }
                bars.append(temp)
        

        for i in range (0, len(x_labels)):

            x_labels[i]['ID'] = i + 1
            x_labels[i]['text'] = x_labels[i].pop('text')

            temp = list(map(x_labels[i].pop('boundingBox').__getitem__, [0, 1, 4, 5]))
            temp[0] /= d[1]
            temp[1] /= d[0]
            temp[2] /= d[1]
            temp[3] /= d[0]

            x_labels[i]['coords'] = temp
            x_labels[i]['centroid'] = [0.5*(x_labels[i]['coords'][0] + x_labels[i]['coords'][2]), 0.5*(x_labels[i]['coords'][1] + x_labels[i]['coords'][3])]
            x_labels[i]['area'] = (x_labels[i]['coords'][2] - x_labels[i]['coords'][0])*(x_labels[i]['coords'][3] - x_labels[i]['coords'][1])
        
        output = {
                    "type": chart_type,
                    "dimensions": [d[0], d[1]],
                    "title": title, 
                    "y_range": {
                        "min": str(chartinfo[3]), 
                        "max": str(chartinfo[4])
                            }, 
                    "x_labels": x_labels,
                    "bars": bars
                }

    if (type_no == 1):

        for i in range (0, len(pixel_points)):
            if (len(pixel_points[i]) != 2):
                print ("ERRORRR!!!!")
            else:
                pixel_points[i][0] /= d[1]
                pixel_points[i][1] /= d[0]

        for i in range (0, len(x_labels)):

            x_labels[i]['ID'] = i + 1
            x_labels[i]['text'] = x_labels[i].pop('text')

            temp = list(map(x_labels[i].pop('boundingBox').__getitem__, [0, 1, 4, 5]))
            temp[0] /= d[1]
            temp[1] /= d[0]
            temp[2] /= d[1]
            temp[3] /= d[0]

            x_labels[i]['coords'] = temp
            x_labels[i]['centroid'] = [0.5*(x_labels[i]['coords'][0] + x_labels[i]['coords'][2]), 0.5*(x_labels[i]['coords'][1] + x_labels[i]['coords'][3])]
            x_labels[i]['area'] = (x_labels[i]['coords'][2] - x_labels[i]['coords'][0])*(x_labels[i]['coords'][3] - x_labels[i]['coords'][1])
            

        peaks, dips = findPeaksDips(data)

        output = {
                    "type": chart_type,
                    "dimensions": [d[0], d[1]],
                    "title": title, 
                    "y_range": {
                        "min": str(chartinfo[3]), 
                        "max": str(chartinfo[4])
                            }, 
                    "x_labels": x_labels,
                    "peaks": [],
                    "dips": []
                }

        for i in range (0, len(peaks)):
            current_peak_info = {
                                "ID": i+1, 
                                "x_label": x_labels[data[peaks[i]][2]]['text'], 
                                "value": round(data[peaks[i]][1]),
                                "coords": pixel_points[peaks[i]]
                                }
            output['peaks'].append(current_peak_info)

        for i in range (0, len(dips)):
            current_dip_info = {
                                "ID": i+1, 
                                "x_label": x_labels[data[dips[i]][2]]['text'], 
                                "value": round(data[dips[i]][1]),
                                "coords": pixel_points[dips[i]]
                                }
            output['dips'].append(current_dip_info)

    if (type_no == 2):

        for i in range (len(pixel_points)):
            for j in range (0, 3):
                pixel_points[i][j] = list(pixel_points[i][j])
                pixel_points[i][j][0] /= d[1]
                pixel_points[i][j][1] /= d[0]

        sectors = []
        for i in range (len(data)):
            sector_info = {
                "ID": i + 1,
                "value": (data[i]/360)*100,
                "center": pixel_points[i][0],
                "arc_coords": {
                    "start": pixel_points[i][1],
                    "end": pixel_points[i][2]
                }
            }
            sectors.append(sector_info)

        output = {
            "type": chart_type,
            "dimensions": [d[0], d[1]],
            "title": title, 
            "sectors": sectors
        }

    os.remove('./input.png')

    return output
