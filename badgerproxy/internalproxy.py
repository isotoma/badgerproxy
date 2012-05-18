import os
import string
from urllib import unquote
import StringIO

from twisted.web.static import File
from twisted.web.server import Request
from twisted.python import log


class InternalProxier(object):

    def __init__(self, root, host, port):
        assert host == "badger"
        assert port == 80

        self.root = root
        self.host = host
        self.port = port

        self.site = File(os.path.join(os.path.dirname(__file__), "public_html"))

    def permitted(self):
        return True

    def get_request(self, method, uri, clientproto, headers, data, response):
        self.transport = response.transport

        r = Request(self, False)
        r.method = method
        r.clientproto = clientproto
        r.path = uri
        r.client = response.client
        r.host = self.host
        r.prepath = []
        r.postpath = map(unquote, string.split(r.path[1:], '/'))
        r.content = StringIO.StringIO(data)
        r.transport = response.transport

        return r

    def proxy(self, method, uri, clientproto, headers, data, response):
        req = self.get_request(method, uri, clientproto, headers, data, response)
        resource = self.site
        log.msg(resource)
        while req.postpath and not resource.isLeaf:
            pathElement = req.postpath.pop(0)
            req.prepath.append(pathElement)
            resource = resource.getChildWithDefault(pathElement, req)
            log.msg(resource)
        req.render(resource)

    proxy_ssl = proxy

    def requestDone(self, *args, **kwargs):
        pass

