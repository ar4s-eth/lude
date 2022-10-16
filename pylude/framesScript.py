#!/usr/bin/env python

import csv
import os


DEFAULT_WORD_PAUSE_MILLISECOND = '500'
if 'LVG_WORD_PAUSE_MS' in os.environ.keys():
    DEFAULT_WORD_PAUSE_MILLISECOND = os.environ['LVG_WORD_PAUSE_MS']


def script_to_framedata(framedata_dir, script_filepath, word_pause):
    lvg_framedata_file = os.path.join(
        framedata_dir,
        os.path.basename(script_filepath)
    )
    script_lines = open(script_filepath, encoding='utf-8').readlines()

    with open(lvg_framedata_file, 'w', newline='') as file:
        writer = csv.writer(file)
        for line in script_lines:
            line_to_framedata(writer, line, word_pause)
    return lvg_framedata_file


def line_to_framedata(writer, line, word_pause):
    for shabda in line.strip().split():
        line_list = [shabda, word_pause, ""]
        writer.writerow(line_list)
    # on decipher consecutive linebreak would mean explicit pagebreak
    writer.writerow(["", word_pause, "LINEBREAK"])


def generate_framedata(script_filepath, framedata_dir):
    try:
        lvg_framedata_file = script_to_framedata(
            framedata_dir,
            script_filepath,
            DEFAULT_WORD_PAUSE_MILLISECOND
        )
        print(lvg_framedata_file)
        return lvg_framedata_file
    except Exception as e:
        print(e)
        return None
