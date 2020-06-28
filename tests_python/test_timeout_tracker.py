from _pydevd_bundle import pydevd_timeout
from _pydevd_bundle.pydevd_constants import IS_PYPY, IS_CPYTHON
from _pydevd_bundle.pydevd_timeout import create_interrupt_this_thread_callback
from tests_python.debugger_unittest import wait_for_condition
import pytest
import threading
import time


@pytest.fixture(autouse=True)
def _enable_debug_msgs():
    original = pydevd_timeout._DEBUG
    pydevd_timeout._DEBUG = True
    yield
    pydevd_timeout._DEBUG = original


def test_timeout():

    class _DummyPyDb(object):

        def __init__(self):
            self.created_pydb_daemon_threads = {}

    raise_timeout = pydevd_timeout.create_interrupt_this_thread_callback()

    def on_timeout(arg):
        assert arg == 1
        raise_timeout()

    py_db = _DummyPyDb()
    timeout_tracker = pydevd_timeout.TimeoutTracker(py_db)
    try:
        if IS_PYPY:
            timeout = 2
        else:
            timeout = 20
        with timeout_tracker.call_on_timeout(1, on_timeout, kwargs={'arg': 1}):
            time.sleep(timeout)
    except KeyboardInterrupt:
        pass


@pytest.mark.skipif(not IS_CPYTHON, reason='This only works in CPython.')
def test_create_interrupt_this_thread_callback():

    class MyThread(threading.Thread):

        def __init__(self):
            threading.Thread.__init__(self)
            self.finished = False
            self.daemon = True
            self.interrupt_thread = None
            self.interrupted = False

        def run(self):
            try:
                self.interrupt_thread = create_interrupt_this_thread_callback()
                while True:
                    time.sleep(.2)
            except KeyboardInterrupt:
                self.interrupted = True
            finally:
                self.finished = True

    t = MyThread()
    t.start()
    wait_for_condition(lambda: t.interrupt_thread is not None)

    t.interrupt_thread()

    wait_for_condition(lambda: t.finished)

    assert t.interrupted


def test_interrupt_main_thread():

    class MyThread(threading.Thread):

        def __init__(self, interrupt_thread_callback):
            threading.Thread.__init__(self)
            self.interrupt_thread_callback = interrupt_thread_callback

        def run(self):
            time.sleep(.5)
            self.interrupt_thread_callback()

    initial_time = time.time()
    if IS_PYPY:
        timeout = 2
    else:
        timeout = 20
    try:
        t = MyThread(create_interrupt_this_thread_callback())
        t.start()
        time.sleep(timeout)
    except KeyboardInterrupt:
        if not IS_PYPY:
            assert time.time() - initial_time < timeout
    else:
        raise AssertionError('Expected main thread to be interrupted.')
