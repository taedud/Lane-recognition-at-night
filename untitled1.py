# -*- coding: utf-8 -*-
"""Untitled1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1mX4fWvjhmsK-efAZ_W1EAY5JqDI0wvcQ
"""

import sys
import os
import cv2
import torch
from matplotlib import pyplot as plt
import numpy as np
from google.colab.patches import cv2_imshow

# saturarion
def saturation(value):
    if value > 255:
        value = 255
    return value

# 히스토그램의 누적을 구함
def histogram_sum(histogram):
    sum_histo = np.zeros(256)
    sum_histo[0] = histogram[0]
    for n in range(1, 256):
        sum_histo[n] = histogram[n] + sum_histo[n-1]
    sum_histo = sum_histo.astype(np.int32)
    return sum_histo

# max, min의 threshold를 받아서 영역안에서 스트레칭
def strech(yuv, max_th, min_th, height, width):
    new_yuv = yuv.copy()
    for h in range(height):
        for w in range(width):
            if yuv[h, w, 0] <= min_th:
                new_yuv[h, w, 0] = 0
            elif yuv[h, w, 0] >= max_th:
                new_yuv[h, w, 0] = 255
            else: #값의 사이는 스트레칭
                new_yuv[h, w, 0] = saturation((int)(
                    (yuv[h, w, 0] - min_th)*255/(max_th - min_th)))
    return new_yuv

#영상 픽셀 개수의 퍼센테이지를 구해 범위내는 스트레칭
def min_max_streching(yuv, sum_histogram, height, width):
    min_per = (int)(((height/2)*width)*0.01)
    max_per = (int)(((height/2)*width)*0.99)

    for n in range(256):
        if sum_histogram[n] > min_per:
            min_histo = n
            break

    for n in range(256):
        if sum_histogram[n] > max_per:
            max_histo = n
            break
    #임계값을 넘겨 스트레칭을 진행
    streching = strech(yuv, max_histo, min_histo, height, width)
    return streching

# 원하는 구역에만 선을 그리기 위해 관심영역 추출
def ROI(img, vertices1, vertices2):
    # 영상과 같은 크기의 0으로 초기화된 mask 생성
    mask = np.zeros_like(img)
    # 영상마다 채널 값이 달라 다르게 설정
    if len(img.shape) > 2:
        color = (255, 255, 255)
    else:  # 흑백 이미지 일때
        color = 255

    # 도로 중앙에 글씨가 존재해 글씨까지
    # 엣지가 검출되는 것을 방지하기 위해 두개 영역 사용
    # 설정영역을 채운다
    cv2.fillPoly(mask, vertices1, color)
    cv2.fillPoly(mask, vertices2, color)

    # and 연산으로 공통되는 부분만 출력
    roi_image = cv2.bitwise_and(img, mask)
    return roi_image

def hough_lines(img, rho, theta, threshold, minlinelength, maxlinegap):  # 허프 변환
    lines = cv2.HoughLinesP(img, rho, theta, threshold, np.array(
        []), minLineLength=minlinelength, maxLineGap=maxlinegap)  # 선 검출
    line_img = np.zeros(
        (img.shape[0], img.shape[1], 3), dtype=np.uint8)  # 선을 그릴 이미지

    # 선 그리기
    if lines is not None:
        for n in range(lines.shape[0]):
            # 라인을 그릴 좌표를 얻어
            point1 = (lines[n][0][0], lines[n][0][1])
            point2 = (lines[n][0][2], lines[n][0][3])

            # 영상에 그린다
            cv2.line(line_img, point1, point2, (0, 0, 255), 2)

    return line_img

#차선을 얻은 영상을 원래 영상에 합친다
def add_img(ori_img, img):  
    return cv2.addWeighted(ori_img, 1, img, 1, 0)

cap = cv2.VideoCapture("주행영상.mp4")

if not cap.isOpened():
    print("Could not Open")
    exit(0)

cap_length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
cap_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

fourcc = cv2.VideoWriter_fourcc(*'XVID')
delay = int(1000 / fps)

out_video = cv2.VideoWriter("outvideo.avi",fourcc, fps, (cap_width, cap_height))

while True: 
    ret, frame = cap.read()
    height, width, _ = frame.shape

    # yuv 변환
    yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    # y의 히스토그램
    # 밤 하늘은 0의 값과 큰 차이가 없어 영상를 가로로 절반 잘라서 구함
    histogram = np.zeros(256)

    for h in range((int)(height/2), height):
      for w in range(width):
         histogram[yuv[h, w, 0]] += 1

    sumofhistogram = histogram_sum(histogram)
    yuv_streching = min_max_streching(yuv, sumofhistogram, height, width)
    dark_img = cv2.cvtColor(yuv_streching, cv2.COLOR_YUV2BGR)


    # 그레이 변환
    gray = cv2.cvtColor(dark_img, cv2.COLOR_BGR2GRAY)

    # 가우시안블러 필터로 노이즈 제거
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    # 캐니엣지로 엣지 추출
    canny = cv2.Canny(blur, 50, 210)

    # 관심영역 설정
    # 차선이 두개이므로 양쪽 차선을 얻기 위해 두개의 관심영역 설정
    vertices1 = np.array([[(460, 400),(280, 550), (410, 550), (590, 400)
                         ]], dtype=np.int32)
    vertices2 = np.array([[(680, 400), (830, 550),(950, 550), (740, 400)
                          ]], dtype=np.int32)
    roi_img = ROI(canny, vertices1, vertices2)
    hough_img = hough_lines(roi_img, 1, np.pi/180, 20, 10, 30)

    result = add_img(dark_img, hough_img)
    
    out_video.write(result)
    if cv2.waitKey(1) == 27:
        break


cap.release()
out_video.release()
cv2.destroyAllWindows()