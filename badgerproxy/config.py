import os
from yay.config import Config

class ProxyConfig(object):

    def __init__(self, d):
        self.d = d

    def __getattr__(self, m):
        return self.d.get(m, None)


def load_config(uri):
    basedir = os.path.dirname(uri)
    c = Config(searchpath=[basedir])
    c.load_uri(uri)
    return ProxyConfig(c.get())

