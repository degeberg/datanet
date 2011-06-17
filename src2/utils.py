import re

from proxy import Headers

def parse_request(req):
    headers = Headers()
    lines = req.splitlines()
    r = re.match('^(.+) (.+) (.+)$', lines.pop(0))

    h = re.compile('^(.+?):(?: (.*))?')

    cur = lines.pop(0)
    while cur != '':
        m = h.match(cur)
        if not m: break
        key, value = m.group(1, 2)
        if value == None:
            value = ''
        headers.addheader(key, value)
        cur = lines.pop(0)
    
    return {
        'version': r.group(1),
        'uri': r.group(2),
        'method': r.group(3),
        'headers': headers,
        'body': '\n'.join(lines)
    }

def pkcs7_pad(data, block_size=16):
    r = len(data) % block_size
    if r == 0: return data
    r = block_size - r
    return data + chr(r) * r
