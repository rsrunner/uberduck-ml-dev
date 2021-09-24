# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/exec.select_speakers.ipynb (unless otherwise specified).

__all__ = ['Dataset', 'select_speakers', 'parse_args', 'STANDARD_MULTISPEAKER', 'STANDARD_SINGLESPEAKER', 'VCTK',
           'FORMATS']

# Cell
import argparse
from collections import namedtuple
from dataclasses import dataclass
import json
import os
from pathlib import Path
from shutil import copyfile, copytree
import sys
from typing import List

STANDARD_MULTISPEAKER = "standard-multispeaker"
STANDARD_SINGLESPEAKER = "standard-singlespeaker"
VCTK = "vctk"
FORMATS = [
    STANDARD_MULTISPEAKER,
    STANDARD_SINGLESPEAKER,
    VCTK,
]


@dataclass
class Dataset:
    path: str
    format: str = STANDARD_MULTISPEAKER
    speakers: str = None


def _convert_to_multispeaker(f, out_path: str, ds: Dataset, start_speaker_id: int):
    assert (
        ds.format == STANDARD_MULTISPEAKER
    ), f"Only {STANDARD_MULTISPEAKER} is supported"
    root = ds.path

    speaker_id = start_speaker_id
    print(ds.format)
    print(ds.path)
    print(ds.speakers)
    if ds.speakers:
        speakers = ds.speakers.split(",")
    else:
        speakers = os.listdir(root)
    for speaker in speakers:
        path = Path(root) / Path(speaker)
        files = os.listdir(path)
        transcriptions, *_ = [f for f in files if f.endswith(".txt")]
        with (Path(root) / speaker / transcriptions).open("r") as txn_f:
            transcriptions = txn_f.readlines()
        for line in transcriptions:
            line = line.strip("\n")
            try:
                line_path, line_txn = line.split("|")
            except Exception as e:
                print(e)
                print(line)
                raise
            line = f"{str(Path(speaker) / Path(line_path))}|{line_txn}"
            f.write(f"{line}|{speaker_id}\n")
        wavs_dvc = path / "wavs.dvc"
        speaker_out_path = Path(out_path) / speaker
        if not speaker_out_path.exists():
            os.makedirs(speaker_out_path)
        if wavs_dvc.exists():
            copyfile(wavs_dvc, speaker_out_path / "wavs.dvc")
        wavs_dir = path / "wavs"
        if wavs_dir.exists():
            copytree(wavs_dir, speaker_out_path / "wavs")
        speaker_id += 1
    return speaker_id - start_speaker_id


def select_speakers(datasets: List[Dataset], out_dir):
    speaker_id = 0
    out_path = Path(out_dir)
    if not out_path.exists():
        os.makedirs(out_path)
    with (out_path / "list.txt").open("w") as f:
        for ds in datasets:
            speaker_count = _convert_to_multispeaker(f, out_path, ds, speaker_id)
            speaker_id += speaker_count


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", help="Path to dataset out directory", default="./dataset")
    parser.add_argument("--config", help="path to JSON config")
    parser.add_argument("-d", "--dataset", action="append", nargs="*")
    return parser.parse_args(args)


try:
    from nbdev.imports import IN_NOTEBOOK
except:
    IN_NOTEBOOK = False

if __name__ == "__main__" and not IN_NOTEBOOK:
    args = parse_args(sys.argv[1:])
    if args.config:
        config = json.load(args.config)
        dataset = config["dataset"]
    elif args.dataset:
        dataset = args.dataset
    else:
        raise Exception("Dataset must be specified")
    dataset_collection = [Dataset(*d) for d in dataset]
    select_speakers(dataset_collection, args.out)