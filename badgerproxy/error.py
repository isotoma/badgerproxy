
class ErrorResponse(object):

    errorcode = 404
    error = "Not found"
    detail = None

    def __init__(self, father, detail=None):
        self.father = father
        self.detail = detail

    def render(self):
        self.father.setResponseCode(self.errorcode, self.error)
        self.father.responseHeaders.addRawHeader("Content-Type", "text/html")
        self.father.write("<h1>%s</h1>" % self.error)
        if self.detail:
            self.father.write("<p>%s</p>" % self.detail)
        self.father.finish()


class ForbiddenResponse(ErrorResponse):

    errorcode = 403
    error = "Forbidden"


