import urllib.parse

CODES = {
    100: 'Continue',
    101: 'Switching Protocols',

    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',

    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',

    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',

    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
}


class HTTPError(Exception):
    def __init__(self, code):
        self.code = code

    def get_code():
        return self.code

    def __str__():
        if self.code in CODES:
            return "%d %s" % (code, CODES[code])
        else:
            return str(code)

    def get_msg():
        if self.code in CODES:
            return CODES[code]
        else:
            return ''

class UserError(HTTPError):
    pass

class ServerError(HTTPError):
    pass

def parse_request(req):
    lines = req.split("\r\n")
    try:
        method, path, protocol = lines.pop(0).split(' ')
    except Exception:
        raise UserError(400)

    r = {
        'method': method,
        'path': path,
        'protocol': protocol,
        'headers': {}
    }

    for header in lines:
        if header == '': continue
        key, value = header.split(': ', 1)
        r['headers'][key] = value

    return r

def parse_request_uri(uri):
    res = urllib.parse.urlparse(uri)
    
    return {
        'path': res.path,
        'query': urllib.parse.parse_qs(res.query),
    }

def create_response(code, headers, body=None):
    return ''
