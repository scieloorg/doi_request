class CrossrefExceptions(Exception):
    pass


class ComunicationError(CrossrefExceptions):
    pass


class RequestError(ComunicationError):
    pass


class UnkownSubmission(CrossrefExceptions):
    pass


class ChainAborted(Exception):
    pass


class RelatedDocumentNotFound(Exception):
    pass
