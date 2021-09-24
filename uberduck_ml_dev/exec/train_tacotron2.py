# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/exec.train_tacotron2.ipynb (unless otherwise specified).

__all__ = ['parse_args']

# Cell
import argparse
import json
import sys

from ..trainer.base import TTSTrainer, MellotronTrainer
from ..vendor.tfcompat.hparam import HParams
from ..models.mellotron import DEFAULTS as MELLOTRON_DEFAULTS

def parse_args(args):
    parser= argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to JSON config")
    args = parser.parse_args(args)
    return args


# Cell
try:
    from nbdev.imports import IN_NOTEBOOK
except:
    IN_NOTEBOOK = False
if __name__ == "__main__" and not IN_NOTEBOOK:
    args = parse_args(sys.argv[1:])
    config = MELLOTRON_DEFAULTS.values()
    if args.config:
        with open(args.config) as f:
            config.update(json.load(f))
    hparams = HParams(**config)
    trainer = MellotronTrainer(hparams)
    try:
        trainer.train()
    except Exception as e:
        print(f"Exception raised while training: {e}")
        # TODO: save state.
        raise e