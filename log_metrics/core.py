# -*- coding: utf-8 -*-

"""
log_metrics.core
~~~~~~~~~~~~~~~~~

This module implements the basic interfaces for our log-metrics package.
"""


import time
import logging
from functools import wraps
import sys
import os


class ContextDecorator(object):
    before = None
    after = None

    def __call__(self, f):
        @wraps(f)
        def inner(*args, **kw):
            if self.before is not None:
                self.before()
            exc = (None, None, None)
            try:
                result = f(*args, **kw)
            except Exception:
                exc = sys.exc_info()
            catch = False
            if self.after is not None:
                catch = self.after(*exc)
            if not catch and exc != (None, None, None):
                raise exc[1]
            return result
        return inner

    def __enter__(self):
        if self.before is not None:
            return self.before()

    def __exit__(self, *exc):
        catch = False
        if self.after is not None:
            catch = self.after(*exc)
        return catch


class Timer(ContextDecorator):
    def __init__(self, name, metrics):
        self.name = name
        self.metrics = metrics

    def before(self):
        self.start = time.time()

    def after(self, *exc):
        duration = "%.2f" % ((time.time() - self.start)*1000)
        self.metrics.measure("%s.ms" % self.name, duration)


class Logger(object):

    def __init__(self, source=None, prefix=None, **kwargs):
        self.source = source or os.environ.get('LOG_METRICS_SOURCE')
        self.prefix = prefix or os.environ.get('LOG_METRICS_PREFIX')

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)

    def timer(self, name):
        return Timer(name, self)

    def increment(self, name, val=None):
        val = val or 1
        self._handler(self._generate("count", name, val))
        return self

    def sample(self, name, val):
        self._handler(self._generate("sample", name, val))
        return self

    def measure(self, name, val):
        self._handler(self._generate("measure", name, val))
        return self

    def unique(self, name, val):
        self._handler(self._generate("unique", name, val))
        return self
        
    def _generate(self, measurement_type, name, value):
        val = "%s#" % measurement_type
        if self.prefix:
            val = "%s%s." % (val, self.prefix)
        val += "%s=%s" % (name, value)
        return val

    def _log(self, val):
        if self.source:
            val = "source=%s %s" % (self.source, val)
        self.logger.info(val)


class GroupMetricsLogger(Logger):

    def __init__(self, *args, **kwargs):
        super(GroupMetricsLogger, self).__init__(*args, **kwargs)
        self.reset()

    def __enter__(self):
        return self

    def __exit__(self, *exe):
        self.emit()

    def emit(self):
        if self._metrics:
            self._log(' '.join(self._metrics))
        self.reset()

    def reset(self):
        self._metrics = []

    def _handler(self, val):
        self._metrics.append(val)


class MetricsLogger(Logger):

    def _handler(self, val):
        self._log(val)
