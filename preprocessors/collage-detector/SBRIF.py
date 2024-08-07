# Copyright (c) 2023 IMAGE Project, Shared Reality Lab, McGill University
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
# <https://github.com/Shared-Reality-Lab/IMAGE-server/blob/main/LICENSE>.

import math
import cv2
import numpy as np


class SbRIF:

    def __init__(self, t=0.7, c=5, s=5, rescale_size=350):
        """
        Initialization of a model instance, t determines the confidence level,
        c and s are pixel-level constants (# of pixels) - c determines size of
        the intersection and s determines suppression (used to remove
        overlapping intersections), rescale_size determines the size of the
        rescaled images (without the preservation of aspect ratio). In most of
        the cases, do not modify c, s and rescale_size.
        Args:
            t: float
            c: int
            s: int
            rescale_size: int
        """
        self.t_cnt = int(math.tan(t * math.pi / 2))
        self.c = c
        self.s = s
        self.rescale_size = rescale_size

    def edge_filter(self, img):
        """
        Canny edge detection.
        Args:
            img: the image
        """
        img = cv2.resize(img,
                         (self.rescale_size, self.rescale_size),
                         interpolation=cv2.INTER_AREA)
        edges = cv2.Canny(img, 50, 200)
        gray_edges = cv2.bitwise_not(edges)

        return gray_edges

    def morphological_operator(self, gray_edges):
        """
        Morphological operations, filters horizontal and vertical edges.
        Args:
            gray_edges: gray-scale image after edge detection
        """
        bw = cv2.adaptiveThreshold(
            gray_edges,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY, 5, -2)
        h = np.copy(bw)
        v = np.copy(bw)

        cols = h.shape[1]
        h_size = cols // 6
        h_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (h_size, 1))
        h = cv2.erode(h, h_structure)
        h = cv2.dilate(h, h_structure)

        rows = v.shape[0]
        v_size = rows // 6
        v_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_size))
        v = cv2.erode(v, v_structure)
        v = cv2.dilate(v, v_structure)

        return v+h

    # hyper-params are in pixel-level
    def regional_identity_filter(self, vh, crosshair, suppression):
        """
        Filtering intersections.
        Args:
            vh: vertical and horizontal edges
            crosshair: the size of the intersection
            suppression: the threshold for calculating L2 norm
        """
        def padding(arr2d, size):
            """
            Padding zeros to the image.
            Args:
                arr2d: the image
                size: the padding size
            """
            padded_img = np.zeros(
                (arr2d.shape[0] + (2 * size), arr2d.shape[1] + (2 * size))
                )
            padded_img[
                size: size + arr2d.shape[0],
                size: size + arr2d.shape[1]
                ] = arr2d

            return padded_img

        padded = padding(vh, crosshair)

        # window_size should be (2n+1, 2n+1)
        def sliding_window(arr2d, window_size):
            """
            Using a sliding window to filter intersections.
            Args:
                arr2d: the image
                window_size: (2n+1, 2n+1)
            """
            intersection_list = []
            for r in range(0, arr2d.shape[0] - window_size[0] + 1):
                for c in range(0, arr2d.shape[1] - window_size[1] + 1):
                    current_window = arr2d[
                        r: r + window_size[0],
                        c: c + window_size[1]
                        ]
                    center_idx = (int(window_size[0] / 2),
                                  int(window_size[1] / 2))

                    # check v and h intersections
                    # check v up and down
                    vup = True
                    for window_r in range(0, center_idx[0]):
                        if current_window[window_r][center_idx[1]] == 0:
                            vup = False
                            break
                    vdown = True
                    for window_r in range(center_idx[0] + 1, window_size[0]):
                        if current_window[window_r][center_idx[1]] == 0:
                            vdown = False
                            break
                    # check r left and right
                    hleft = True
                    for window_c in range(0, center_idx[1]):
                        if current_window[center_idx[0]][window_c] == 0:
                            hleft = False
                            break
                    hright = True
                    for window_c in range(center_idx[1] + 1, window_size[1]):
                        if current_window[center_idx[0]][window_c] == 0:
                            hright = False
                            break

                    # if this is an intersection
                    if (vup or vdown) and (hleft or hright):
                        intersection_list.append((r, c, 1))

            return intersection_list

        intersec_list = sliding_window(padded, (2 * crosshair + 1,
                                                2 * crosshair + 1))

        def suppression_l2(list_mask, s):
            """
            Suppressing similar points by applying L2.
            Args:
                list_mask: Masking out suppressed points
                s: threshold for L2 norm
            """
            def dist(x1, x2):

                return math.sqrt((x1[0] - x2[0]) ** 2 + (x1[1] - x2[1]) ** 2)

            for i in range(0, len(list_mask) - 1):
                if list_mask[i][2] == 1:
                    for ii in range(i + 1, len(list_mask)):
                        if list_mask[ii][2] == 1 and dist(list_mask[i],
                                                          list_mask[ii]) <= s:
                            list_mask[ii] = (list_mask[ii][0],
                                             list_mask[ii][1], 0)

            return list_mask

        intersec_list = suppression_l2(intersec_list, suppression)

        return intersec_list

    # hyper-params
    # t_cnt: positive integer number
    # cross_hair: pixel-level, positive integer number
    # suppression: pixel-level, positive real number
    def inference(self, img):
        """
        Inference on one image and returning the boolean result.
        Args:
            img: the image
        """
        gray_edges = self.edge_filter(img)
        vh = self.morphological_operator(gray_edges)
        list = self.regional_identity_filter(vh, crosshair=self.c,
                                             suppression=self.s)
        cnt = 0
        for x in list:
            if x[2] == 1:
                cnt += 1

        return cnt >= self.t_cnt
