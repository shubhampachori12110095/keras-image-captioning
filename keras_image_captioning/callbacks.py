import numpy as np

from datetime import datetime
from keras import backend as K
from keras.callbacks import Callback

from .inference import BasicInference
from .io_utils import logging


class LogLearningRate(Callback):
    def on_epoch_end(self, epoch, logs):
        logs['learning_rate'] = K.get_value(self.model.optimizer.lr)


class LogTimestamp(Callback):
    def on_epoch_begin(self, epoch, logs):
        self._ts_start = self._get_current_ts()

    def on_epoch_end(self, epoch, logs):
        logs['ts_start'] = self._ts_start
        logs['ts_end'] = self._get_current_ts()

    def _get_current_ts(self):
        # Workaround for a CSVLogger's bug
        class NotIterableStr(object):
            def __init__(self, value):
                self._value = value

            def __str__(self):
                return self._value

        return NotIterableStr(datetime.utcnow().isoformat(' '))


class LogMetrics(Callback):
    def __init__(self, dataset_provider):
        super(LogMetrics, self).__init__()
        self._dataset_provider = dataset_provider

    def on_train_begin(self, logs):
        # Initialization is here, not in __init__ because in there self.model
        # is not initialized yet
        self._inference = BasicInference(self.model, self._dataset_provider)

    def on_epoch_end(self, epoch, logs):
        logs.update({k: np.float32(v) for k, v
                     in self._inference.evaluate_training_set().items()})
        logs.update({'val_' + k: np.float32(v) for k, v
                     in self._inference.evaluate_validation_set().items()})


class StopAfterTimedelta(Callback):
    def __init__(self, timedelta, verbose=0):
        super(StopAfterTimedelta, self).__init__()
        self._timedelta = timedelta
        self._verbose = verbose

    def on_train_begin(self, logs):
        self._dt_start = datetime.utcnow()
        self._stopped_epoch = None

    def on_epoch_end(self, epoch, logs):
        if self._timedelta is None:
            return
        if datetime.utcnow() - self._dt_start > self._timedelta:
            self.model.stop_training = True
            self._stopped_epoch = epoch

    def on_train_end(self, logs):
        if self._stopped_epoch is not None and self._verbose > 0:
            logging('Epoch {}: stop after {}'.format(self._stopped_epoch,
                                                     self._timedelta))
