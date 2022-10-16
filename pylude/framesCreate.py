#!/usr/bin/env python

import csv
import math
import os
import random
import re
from PIL import Image, ImageDraw, ImageFont
import functools

def do_generate_frames(framedata_file, frames_dir, frame_specs):
    @functools.lru_cache(maxsize=128)
    def line_need_break(line):
        if bool(re.match(r".*[\.,!\:;\?]\s*$", line)):
            return True
        return False


    @functools.lru_cache(maxsize=128)
    def last_line_y(current_y):
        return current_y - (FRAME_SPECS['font_height'] + FRAME_SPECS['default_line_gap'])


    @functools.lru_cache(maxsize=128)
    def next_line_y(current_y):
        return current_y + FRAME_SPECS['font_height'] + FRAME_SPECS['default_line_gap']


    @functools.lru_cache(maxsize=128)
    def line_x_middle(line_width, shabda_width):
        x_text = (FRAME_SPECS['width'] - line_width) / 2
        if (line_width + shabda_width) < FRAME_SPECS['width']: x_text -= (shabda_width/2)
        return x_text


    @functools.lru_cache(maxsize=128)
    def line_shabda_x_middle(line_width, shabda_width):
        x_text = line_x_middle(line_width, shabda_width)
        x_shabda = (FRAME_SPECS['width'] - shabda_width) / 2
        if (x_text + line_width + shabda_width + FRAME_SPECS['margin_left_right']) < FRAME_SPECS['width']:
            x_shabda = x_text + line_width
        return x_shabda


    @functools.lru_cache(maxsize=128)
    def line_x_left(_line_width, _shabda_width):
        return FRAME_SPECS['margin_left_right']


    @functools.lru_cache(maxsize=128)
    def line_shabda_x_left(line_width, shabda_width):
        x_text = FRAME_SPECS['margin_left_right']
        x_shabda = FRAME_SPECS['margin_left_right']

        if (x_text + line_width + FRAME_SPECS['margin_left_right']) < FRAME_SPECS['width']:
            x_shabda = x_text + line_width - shabda_width
        return x_shabda


    @functools.lru_cache(maxsize=128)
    def line_x(line_width, shabda_width):
        return {
            'default': line_x_middle,
            'middle': line_x_middle,
            'left': line_x_left,
        }[FRAME_SPECS['line_indentation_style']](line_width, shabda_width)


    @functools.lru_cache(maxsize=128)
    def line_shabda_x(line_width, shabda_width):
        return {
            'default': line_shabda_x_middle,
            'middle': line_shabda_x_middle,
            'left': line_shabda_x_left,
        }[FRAME_SPECS['line_indentation_style']](line_width, shabda_width)


    @functools.lru_cache(maxsize=128)
    def next_word_coordinates(line, shabda, y_text, font):
        line_width, _ = font.getsize(line)
        shabda_width, _ = font.getsize(' ' + shabda)
        y_shabda = y_text
        x_text = line_x(line_width, shabda_width)
        x_shabda = line_shabda_x(line_width, shabda_width)
        y_shabda = last_line_y(y_text)
        return (x_shabda, y_shabda)


    @functools.lru_cache(maxsize=128)
    def allowed_line_count(max_height, font, margin_top=10, buffer=0):
        possible_count = int(max_height / (next_line_y(margin_top) + buffer))
        if possible_count < FRAME_SPECS['max_lines_per_frame']:
            return possible_count
        return FRAME_SPECS['max_lines_per_frame']


    def draw_read_line(canvas, lyric_line, y_text, font, shabda_width=0):
        draw = ImageDraw.Draw(canvas)
        line_width, _ = font.getsize(lyric_line)
        if line_need_break(lyric_line):
            shabda_width = 0
        x_text = line_x(line_width, shabda_width)
        draw.text(
            (x_text, y_text),
            lyric_line,
            fill=FRAME_SPECS['textcolor'],
            font=font)
        y_text = next_line_y(y_text)
        del draw
        return y_text


    def draw_next_word(canvas, last_line, shabda, x_coordinates, font, color):
        draw = ImageDraw.Draw(canvas)
        draw.text(
            x_coordinates,
            ' ' + shabda,
            fill=color,
            font=font)
        del draw


    def save_image_times(canvas, frame_index, times, subindex=0):
        for idx in range(0,int(times)):
            frame_filepath = os.path.join(FRAMES_DIR, "lvg-%d-%d.png" % (frame_index, subindex))
            subindex += 1
            canvas.save(frame_filepath, "PNG")
        return subindex

    def create_frame_shabda(canvas, frame_index, y_text, for_millisec, line, shabda, font):
        x_coordinates = next_word_coordinates(line, shabda, y_text, font)

        if len(line) > 0:
            draw_next_word(canvas, line, shabda, x_coordinates, font, FRAME_SPECS['textcolor_next'])

        frames_count = math.ceil(FRAMES_PER_SECOND * (int(for_millisec)/1000))
        subindex = 0
        if len(shabda) < 1:
            subindex = save_image_times(canvas, frame_index, frames_count, subindex)
        if len(shabda) < 2:
            subindex = save_image_times(canvas, frame_index, frames_count/2, subindex)
            draw_next_word(canvas, line, shabda, x_coordinates, font, FRAME_SPECS['textcolor_current'])
            subindex = save_image_times(canvas, frame_index, frames_count/2, subindex)

        elif len(shabda) == 2:
            subindex = save_image_times(canvas, frame_index, int(frames_count/3), subindex)
            draw_next_word(canvas, line, shabda[0], x_coordinates, font, FRAME_SPECS['textcolor_current'])
            subindex = save_image_times(canvas, frame_index, int(frames_count/3), subindex)
            draw_next_word(canvas, line, shabda, x_coordinates, font, FRAME_SPECS['textcolor_current'])
            subindex = save_image_times(canvas, frame_index, int(frames_count/3), subindex)
        else:
            token_size = math.ceil(len(shabda) / 3)
            subindex = save_image_times(canvas, frame_index, int(frames_count/4), subindex)
            draw_next_word(canvas, line, shabda[:(token_size)], x_coordinates, font, FRAME_SPECS['textcolor_current'])
            subindex = save_image_times(canvas, frame_index, int(frames_count/4), subindex)
            draw_next_word(canvas, line, shabda[:(token_size*2)], x_coordinates, font, FRAME_SPECS['textcolor_current'])
            subindex = save_image_times(canvas, frame_index, int(frames_count/4), subindex)
            draw_next_word(canvas, line, shabda, x_coordinates, font, FRAME_SPECS['textcolor_current'])
            subindex = save_image_times(canvas, frame_index, int(frames_count/4), subindex)


    def base_image(bgimage_path):
        try:
            bgimage = Image.open(bgimage_path)
            return bgimage.copy().resize((FRAME_SPECS['width'], FRAME_SPECS['height']))
        except:
            return Image.new('RGB', (FRAME_SPECS['width'], FRAME_SPECS['height']), FRAME_SPECS['bgcolor'])


    def create_frame_image(frame_index, for_millisec, lyric_list, shabda, font):
        canvas = base_image(BASE_IMAGE_FILE)

        y_text = FRAME_SPECS['margin_top']
        lines_to_use = allowed_line_count(FRAME_SPECS['height'], font, y_text)

        line_to_add_from = 0
        if len(lyric_list) > lines_to_use:
            line_to_add_from = len(lyric_list) - lines_to_use

        shabda_width, _ = font.getsize(" " + shabda)

        lines_already_read = lyric_list[line_to_add_from:-1]
        line_currently_read = lyric_list[-1]

        for line in lines_already_read:
            y_text = draw_read_line(canvas, line, y_text, font)

        y_text = draw_read_line(canvas, line_currently_read, y_text, font, shabda_width)

        create_frame_shabda(canvas, frame_index, y_text, for_millisec, line_currently_read, shabda, font)
        # cleaning up to avoid corrupted memory errors
        del canvas

    def text_wrap(frame_lyric, shabda, allowed_characters_in_a_line):
        if len(frame_lyric) == 0:
            frame_lyric.append(shabda)
        elif len(frame_lyric[-1]) == 0:
            frame_lyric[-1] = shabda
        elif (len(frame_lyric[-1]) + 1 + len(shabda)) < allowed_characters_in_a_line: #is_frame_lyric_last_line_vacant
            frame_lyric[-1] = "%s %s" % (frame_lyric[-1], shabda)
        else:
            frame_lyric.append(shabda)

        if shabda[-1] in ['.', '"', ';']:
            frame_lyric.append("")
        return frame_lyric

    def count_allowed_characters_in_a_line(font):
        width_of_one_char = (font.getsize("y")[0])
        usable_frame_space = (FRAME_SPECS['width'] - (2*FRAME_SPECS['margin_left_right']))
        return math.floor(usable_frame_space / width_of_one_char)

    def framedata_to_frames(frame_data_file):
        default_font = ImageFont.truetype(FRAME_SPECS['font_path'], 73, encoding="unic")
        allowed_characters_in_a_line = count_allowed_characters_in_a_line(default_font)
        _, FRAME_SPECS['font_height'] = default_font.getsize("Trying to keep ^~*,| better height")

        os.makedirs(FRAMES_DIR, exist_ok=True)
        with open(frame_data_file) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            frame_lyric = []
            was_last_line_newline = False
            for row in csv_reader:
                shabda = row[0]
                pause_x = row[1]
                instructions = row[2].strip().split()
                if "LINEBREAK" in instructions:
                    if was_last_line_newline:
                        frame_lyric = []
                    was_last_line_newline = True
                    continue
                else:
                    was_last_line_newline = False
                frame_lyric = text_wrap(frame_lyric, shabda, allowed_characters_in_a_line)
                print("%s\t'%s'" % (pause_x, frame_lyric))
                create_frame_image(line_count, pause_x, frame_lyric, shabda, default_font)
                line_count += 1
            print('Processed %d lines for %s.' % (line_count, frame_data_file))

    ## calling this internal structure scoped structure
    FRAME_SPECS = frame_specs
    FRAMES_PER_SECOND = frame_specs['fps']
    BASE_IMAGE_FILE = frame_specs['base_image_file']
    FRAMES_DIR = frames_dir
    framedata_to_frames(framedata_file)


def base_image_path(bgimage_dir):
    try:
        if "LVG_BG_IMAGE_FULL_PATH" in os.environ.keys():
            bgimage_path = os.environ["LVG_BG_IMAGE_FULL_PATH"]
            if os.path.isfile(bgimage_path):
                return bgimage_path
        _bgimages = [img for img in os.listdir(bgimage_dir)
                        if img.endswith(".jpg") or
                        img.endswith(".jpeg") or
                        img.endswith(".png")]
        bgimage_name = _bgimages[random.randint(0, len(_bgimages)-1)]
        return os.path.join(bgimage_dir, bgimage_name)
    except:
        return None


## CONFIG
DEFAULT_FONTS = {
    'caviardreams-bi': 'CaviarDreams_BoldItalic.ttf',
    'caviardreams': 'CaviarDreams.ttf',
    'notosans-black': 'NotoSans-Black.ttf',
    'playfairdisplay-black-i': 'PlayfairDisplay-BlackItalic.otf',
    'playfairdisplay': 'PlayfairDisplay-Regular.otf',
}

DEFAULT_FONT_FILE = DEFAULT_FONTS['caviardreams-bi']

DEFAULT_FRAME_SPECS = {
    'width': 1024,
    'height': 768,
    'margin_top': 100, #10
    'margin_left_right': 50,
    'default_line_gap': 10,
    'max_lines_per_frame': 5,

    #'font_path': DEFAULT_FONT_PATH,
    'font_height': 50,

    'bgcolor': (236, 128, 16), # dull orange
    #'textcolor': (73, 73, 96), # muddy purple
    #'textcolor_current': (64, 64, 255), # blue
    #'textcolor_next': (192, 192, 255), # light purple
    'textcolor': (201, 66, 0), # muddy purple
    'textcolor_current': (255, 103, 38), # blue
    'textcolor_next': (255, 135, 84), # light purple

    'line_indentation_style': 'left', #default
}

DEFAULT_FRAMES_PER_SECOND = 24  ## common across scripts

BGIMAGE_NAME = 'plain' #'musical-night.jpg'


def generate_frames(framedata_file, frames_dir, lvg_dirs, frame_specs=DEFAULT_FRAME_SPECS):
    DEFAULT_FONT_PATH = os.path.join(lvg_dirs['fonts_dir'], DEFAULT_FONT_FILE)
    for default_key, default_val in DEFAULT_FRAME_SPECS.items():
        if default_key not in frame_specs.keys():
            frame_specs[default_key] = default_val
    if 'font_path' not in frame_specs.keys():
        frame_specs['font_path'] = DEFAULT_FONT_PATH
    if 'fps' not in frame_specs.keys():
        frame_specs['fps'] = DEFAULT_FRAMES_PER_SECOND
    if 'base_image_file' not in frame_specs.keys():
        if 'bgimage_id' in frame_specs.keys():
            bgimage_name = frame_specs['bgimage_id'] + '.jpg'
            frame_specs['base_image_file'] = os.path.join(lvg_dirs['bgimages_dir'], bgimage_name)
        else:
            frame_specs['base_image_file'] = os.path.join(lvg_dirs['bgimages_dir'], BGIMAGE_NAME)
    do_generate_frames(framedata_file, frames_dir, frame_specs)
    return frame_specs
