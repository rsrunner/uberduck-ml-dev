# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/exec.force_spectrogram.ipynb (unless otherwise specified).

__all__ = ['parse_args', 'run']

# Cell
import argparse
from collections import namedtuple
from dataclasses import dataclass
import json
import os
from pathlib import Path
from shutil import copyfile, copytree
import sys
import torch
from typing import List, Optional, Set

from tqdm import tqdm

from nemo.collections.tts.models import TalkNetSpectModel


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m", "--model", default="Path to model state dict", required=True
    )
    parser.add_argument("-f", "--filelist", default="Path to filelist", required=True)
    parser.add_argument(
        "-t", "--model-type", help="model type", required=True, default="talknet"
    )
    parser.add_argument("--durations")
    parser.add_argument("--f0s")
    parser.add_argument("--cuda", default=torch.cuda.is_available())
    return parser.parse_args(args)


def run(args):
    if args.model_type != "talknet":
        raise Exception("Supported model types: talknet")
    model = TalkNetSpectModel.restore_from(args.model)
    model.eval()
    durs = torch.load(args.durations)
    f0s = torch.load(args.f0s)
    with open(args.filelist) as f:
        lines = readlines()
    for line in tqdm(lines):
        path = line.split("|")[0].strip()
        line_name, _ = os.path.splitext(os.path.basename(path))
        line_tokens = model.parse(text=line.split("|")[1].strip())
        line_durs = (
            torch.stack(
                (
                    durs[line_name]["blanks"],
                    torch.cat((durs[line_name]["tokens"], torch.zeros(1).int())),
                ),
                dim=1,
            )
            .view(-1)[:-1]
            .view(1, -1)
        )
        x_f0s = f0s[line_name].view(1, -1)
        if args.cuda:
            line_durs = line_durs.cuda()
            x_f0s = x_f0s.cuda()

        spect = model.force_spectrogram(tokens=line_tokens, durs=line_durs, f0=line_f0s)
        out_path = path.replace(".wav", ".npy")
        np.save(out_path, spect.detach().cpu().numpy())


try:
    from nbdev.imports import IN_NOTEBOOK
except:
    IN_NOTEBOOK = False

if __name__ == "__main__" and not IN_NOTEBOOK:
    args = parse_args(sys.argv[1:])
    run(args)