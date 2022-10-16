#!/usr/bin/env python

import os
import cv2
import re
import sys
from PIL import Image


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    '''
    source: https://stackoverflow.com/a/5967539
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]


def listframes(frames_dir):
    _listframes = [img for img in os.listdir(frames_dir)
                    if img.endswith(".jpg") or
                       img.endswith(".jpeg") or
                       img.endswith(".png")]
    _listframes.sort(key=natural_keys)
    return _listframes


def get_video_size(frames_dir, list_of_frames):
    mean_height = 0
    mean_width = 0
    num_of_images = len(list_of_frames)

    for frame in list_of_frames:
        width, height = Image.open(os.path.join(frames_dir, frame)).size
        mean_height += height
        mean_width += width

    mean_height /= num_of_images
    mean_width /= num_of_images
    return (int(mean_width), int(mean_height))


def resize_frames(frames_dir, list_of_frames, size):
    for frame in list_of_frames:
        framepath = os.path.join(frames_dir, frame)
        im = Image.open(framepath)

        imResize = im.resize(size, Image.ANTIALIAS)
        imResize.save(framepath, 'PNG', quality = 100) # setting quality
        # printing each resized image name
        print("resized:", frame)


def do_generate_video(frames_dir, list_of_frames, video_spec):
    video_file = video_spec['filepath']
    video_size = video_spec['size']
    video_fps  = video_spec['fps']
    frame_repeat_count = video_spec['frame-repeat-count']

    fourcc = cv2.VideoWriter_fourcc(*'MJPG')

    video = cv2.VideoWriter(video_file, fourcc, video_fps, video_size, True)

    last_framepath = None
    for frame in list_of_frames:
        print("adding frame:", frame)
        framepath = os.path.join(frames_dir, frame)
        video.write(cv2.imread(framepath))
        last_framepath = framepath
    for _ in range(frame_repeat_count):
        video.write(cv2.imread(last_framepath))

    cv2.destroyAllWindows() # Deallocating memories taken for window creation
    video.release()  # releasing the video generated


def generate_video(frames_dir, video_file, video_fps):
    all_frames = listframes(frames_dir)
    if all_frames == None or len(all_frames) == 0:
        print("found no frames at %s" % (frames_dir))
        sys.exit(1)
    video_size = get_video_size(frames_dir, all_frames)
    #resize_frames(frames_dir, all_frames, video_size)
    video_spec = {
        'filepath': video_file,
        'size': video_size,
        'fps': video_fps,
        'frame-repeat-count': 48,
    }
    do_generate_video(frames_dir, all_frames, video_spec)
