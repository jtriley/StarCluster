#!/usr/bin/env python
import os
import optparse
import mimetypes
import posixpath
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

ERROR_MSG = """\
<head>
<title>DOH!</title>
</head>
<body>
<pre>
 _  _    ___  _  _
| || |  / _ \| || |
| || |_| | | | || |_
|__   _| |_| |__   _|
   |_|  \___/   |_|

</pre>
<h1>Error response</h1>
<p>Error code %(code)d.
<p>Message: %(message)s.
<p>Error code explanation: %(code)s = %(explain)s.
</body>
"""


class MyHandler(BaseHTTPRequestHandler):
    error_message_format = ERROR_MSG

    def do_GET(self):
        try:
            docroot = globals()['DOCUMENTROOT']
            fname = posixpath.join(docroot, self.path[1:])
            #remove query args. query args are ignored in static server
            fname = fname.split('?')[0]
            if fname.endswith('/') or os.path.isdir(fname):
                fname = posixpath.join(fname, 'index.html')
            f = open(fname)  # self.path has /test.html
            content_type = mimetypes.guess_type(fname)[0]
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            while True:
                data = f.read(2097152)
                if not data:
                    break
                self.wfile.write(data)
            #self.wfile.write(f.read())
            f.close()
            return
        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)

    def do_POST(self):
        try:
            print 'no posting!'
        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)


def main(path, interface="localhost", port=8080):
    try:
        docroot = os.path.realpath(path)
        globals()['DOCUMENTROOT'] = docroot
        server = HTTPServer((interface, port), MyHandler)
        print 'started httpserver...'
        print 'document_root = %s' % docroot
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-i", "--interface", dest="interface", action="store",
                      default="localhost")
    parser.add_option("-p", "--port", dest="port", action="store", type="int",
                      default=8080)
    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.error('usage:  webserver.py <document_root>')
    path = args[0]
    main(path, **opts.__dict__)
