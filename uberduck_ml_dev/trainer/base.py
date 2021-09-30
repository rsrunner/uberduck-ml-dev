# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/trainer.base.ipynb (unless otherwise specified).

__all__ = ['TTSTrainer', 'Tacotron2Loss', 'MellotronTrainer']

# Cell
import os
from pprint import pprint

import torch
from torch.cuda.amp import autocast, GradScaler
from torch.utils.tensorboard import SummaryWriter

from ..models.common import MelSTFT


class TTSTrainer:
    def __init__(self, hparams):
        self.hparams = hparams
        for k, v in hparams.values().items():
            setattr(self, k, v)

        self.global_step = 0
        self.writer = SummaryWriter()
        if not hasattr(self, "debug"):
            self.debug = False
        if self.debug:
            print("Running in debug mode with hparams:")
            pprint(hparams.values())
        else:
            print("Initializing trainer with hparams:")
            pprint(hparams.values())

    def save_checkpoint(self, checkpoint_name, **kwargs):
        checkpoint = {}
        for k, v in kwargs.items():
            if hasattr(v, "state_dict"):
                checkpoint[k] = v.state_dict()
            else:
                checkpoint[k] = v
        torch.save(
            checkpoint, os.path.join(self.checkpoint_path, f"{checkpoint_name}.pt")
        )

    def load_checkpoint(self, checkpoint_name):
        return torch.load(os.path.join(self.checkpoint_path, checkpoint_name))

    def log(self, tag, step, scalar=None, audio=None):
        if audio is not None:
            self.writer.add_audio(tag, audio, step)
        if scalar:
            self.writer.add_scalar(tag, scalar, step)


    def sample(self, mel, algorithm="griffin-lim", **kwargs):
        if algorithm == "griffin-lim":
            mel_stft = MelSTFT()
            audio = mel_stft.griffin_lim(mel)
        else:
            raise NotImplemented
        return audio



    def train():
        raise NotImplemented
        # for batch in enumerate(data):
        #    #fill in

# Cell
from typing import List
import torch
from torch import nn
from torch.utils.data import DataLoader
from ..data_loader import TextMelDataset, TextMelCollate
from ..models.mellotron import Tacotron2


class Tacotron2Loss(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, model_output: List, target: List):
        mel_target, gate_target = target[0], target[1]
        mel_target.requires_grad = False
        gate_target.requires_grad = False
        gate_target = gate_target.view(-1, 1)
        mel_out, mel_out_postnet, gate_out, _ = model_output
        gate_out = gate_out.view(-1, 1)
        mel_loss = nn.MSELoss()(mel_out, mel_target) + nn.MSELoss()(
            mel_out_postnet, mel_target
        )
        gate_loss = nn.BCEWithLogitsLoss()(gate_out, gate_target)
        return mel_loss + gate_loss


class MellotronTrainer(TTSTrainer):
    REQUIRED_HPARAMS = [
        "audiopaths_and_text",
        "checkpoint_path",
        "dataset_path",
        "epochs",
        "mel_fmax",
        "mel_fmin",
        "n_mel_channels",
        "text_cleaners",
    ]

    def validate(self, **kwargs):
        model = kwargs["model"]
        val_set = kwargs["val_set"]
        collate_fn = kwargs["collate_fn"]
        criterion = kwargs["criterion"]
        if self.distributed_run:
            raise NotImplemented
        total_loss = 0
        total_steps = 0
        with torch.no_grad():
            val_loader = DataLoader(
                val_set,
                shuffle=False,
                batch_size=self.batch_size,
                collate_fn=collate_fn,
            )
            for batch in val_loader:
                total_steps += 1
                X, y = model.parse_batch(batch)
                y_pred = model(X)
                loss = criterion(y_pred, y)
                total_loss += loss.item()
            mean_loss = total_loss / total_steps
            print(f"Average loss: {mean_loss}")
            self.log("Val/loss", self.global_step, scalar=mean_loss)

    @property
    def training_dataset_args(self):
        return [
            self.dataset_path,
            self.training_audiopaths_and_text,
            self.text_cleaners,
            self.p_arpabet,
            # audio params
            self.n_mel_channels,
            self.sample_rate,
            self.mel_fmin,
            self.mel_fmax,
            self.filter_length,
            self.hop_length,
            self.win_length,
            self.max_wav_value,
            self.include_f0,
        ]

    @property
    def val_dataset_args(self):
        val_args = [a for a in self.training_dataset_args]
        val_args[1] = self.val_audiopaths_and_text
        return val_args

    def train(self):
        train_set = TextMelDataset(
            *self.training_dataset_args,
            debug=self.debug,
            debug_dataset_size=self.batch_size,
        )
        val_set = TextMelDataset(
            *self.val_dataset_args, debug=self.debug, debug_dataset_size=self.batch_size
        )
        collate_fn = TextMelCollate(n_frames_per_step=1, include_f0=self.include_f0)
        train_loader = DataLoader(
            train_set, batch_size=self.batch_size, shuffle=True, collate_fn=collate_fn
        )
        criterion = Tacotron2Loss()

        model = Tacotron2(self.hparams)
        if torch.cuda.is_available():
            model = model.cuda()
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )
        start_epoch = 0
        if self.checkpoint_name:
            checkpoint = self.load_checkpoint(self.checkpoint_name)
            model.load_state_dict(checkpoint["model"])
            optimizer.load_state_dict(checkpoint["optimizer"])
            start_epoch = checkpoint["iteration"]
            # self.global_step = checkpoint["global_step"]
        if self.fp16_run:
            scaler = GradScaler()
        # main training loop
        for epoch in range(start_epoch, self.epochs):
            for batch in train_loader:
                self.global_step += 1
                model.zero_grad()
                X, y = model.parse_batch(batch)
                if self.fp16_run:
                    with autocast():
                        y_pred = model(X)
                        loss = criterion(y_pred, y)
                else:
                    y_pred = model(X)
                    loss = criterion(y_pred, y)

                # TODO: fix for distributed run
                if self.distributed_run:
                    raise NotImplemented
                else:
                    reduced_loss = loss.item()

                if self.fp16_run:
                    scaler.scale(loss).backward()
                    scaler.unscale_(optimizer)
                    grad_norm = torch.nn.utils.clip_grad_norm(
                        model.parameters(), self.grad_clip_thresh
                    )
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    grad_norm = torch.nn.utils.clip_grad_norm(
                        model.parameters(), self.grad_clip_thresh
                    )
                    optimizer.step()
                print(f"Loss: {reduced_loss}")
                self.log("Loss/train", self.global_step, scalar=reduced_loss)
                if epoch % self.steps_per_sample == 0:
                    _, mel_out_postnet, *_ = y_pred
                    audio = self.sample(mel=mel_out_postnet[0])
                    self.log("AudioSample/train", self.global_step, audio=audio)
            if epoch % self.epochs_per_checkpoint == 0:
                self.save_checkpoint(
                    f"mellotron_{epoch}",
                    model=model,
                    optimizer=optimizer,
                    iteration=epoch,
                    learning_rate=self.learning_rate,
                    global_step=self.global_step,
                )

            # Generate an audio sample
            # TODO(zach)

            # There's no need to validate in debug mode since we're not really training.
            if self.debug:
                continue
            self.validate(
                model=model,
                val_set=val_set,
                collate_fn=collate_fn,
                criterion=criterion,
            )