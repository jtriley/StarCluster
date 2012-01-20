import os
import sys
import shlex
import optparse
import mimetypes
import posixpath
import webbrowser
import subprocess
import BaseHTTPServer as httpserv

from starcluster import templates
from starcluster import exception
from starcluster.logger import log

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


class StoppableHttpServer(httpserv.HTTPServer):
    """http server that reacts to self.stop flag"""

    def serve_forever(self):
        """Handle one request at a time until stopped."""
        self.stop = False
        while not self.stop:
            self.handle_request()


class BaseHandler(httpserv.BaseHTTPRequestHandler):
    error_message_format = ERROR_MSG

    def do_GET(self):
        print 'GET not supported'

    def do_POST(self):
        print 'POSTing not supported'

    def do_shutdown(self):
        log.info("Shutting down server...")
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.server.stop = True


class DocrootHandler(BaseHandler):

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


class TemplateHandler(DocrootHandler):
    """
    Simple GET handler that loads and renders files/templates within a package
    under the starcluster.templates package. You can set the _root_template_pkg
    attribute on this class before passing to BaseHTTPServer to specify a
    starcluster.templates subpackage to render templates from. Defaults to
    rendering starcluster.templates (i.e. '/')
    """
    _root_template_pkg = '/'
    _tmpl_context = {}
    _bin_exts = ('.ico', '.gif', '.jpg', '.png')

    def do_GET(self):
        relpath = self.path[1:].split('?')[0]
        if relpath == "shutdown":
            self.do_shutdown()
            return
        fullpath = posixpath.join(self._root_template_pkg, relpath)
        try:
            if relpath.endswith(self._bin_exts):
                data = templates.get_resource(fullpath).read()
            else:
                tmpl = templates.get_web_template(fullpath)
                data = tmpl.render(**self._tmpl_context)
            content_type = mimetypes.guess_type(os.path.basename(relpath))[0]
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(data)
        except IOError, templates.TemplateNotFound:
            self.send_error(404, 'File Not Found: %s' % self.path)
            return


def get_template_server(root_template_pkg='/', interface="localhost",
                        port=None, context={}):
    TemplateHandler._root_template_pkg = root_template_pkg
    TemplateHandler._tmpl_context = context
    server = get_webserver(interface=interface, port=port,
                           handler=TemplateHandler)
    return server


def get_webserver(interface="localhost", port=None, handler=DocrootHandler):
    if port is None:
        port = 0
    server = StoppableHttpServer((interface, port), handler)
    return server


class BackgroundBrowser(webbrowser.GenericBrowser):
    """Class for all browsers which are to be started in the background."""
    def open(self, url, new=0, autoraise=1):
        cmdline = [self.name] + [arg.replace("%s", url)
                                 for arg in self.args]
        try:
            if sys.platform[:3] == 'win':
                p = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
            else:
                setsid = getattr(os, 'setsid', None)
                if not setsid:
                    setsid = getattr(os, 'setpgrp', None)
                p = subprocess.Popen(cmdline, close_fds=True,
                                     preexec_fn=setsid, stdout=subprocess.PIPE)
            return (p.poll() is None)
        except OSError:
            return False


def _is_exe(fpath):
    return os.path.exists(fpath) and os.access(fpath, os.X_OK)


def _which(program):
    fpath, fname = os.path.split(program)
    if fpath:
        if _is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if _is_exe(exe_file):
                return exe_file


def open_browser(url, browser_cmd=None):
    if browser_cmd:
        cmd = shlex.split(browser_cmd)
        arg0 = cmd[0]
        if not _which(arg0):
            raise exception.BaseException("browser %s does not exist" % arg0)
        if "%s" not in browser_cmd:
            cmd.append("%s")
        browser = BackgroundBrowser(cmd)
    else:
        # use 'default' browser from webbrowser module
        browser = webbrowser.get()
    browser_name = getattr(browser, 'name', None)
    if not browser_name:
        browser_name = getattr(browser, '_name', 'UNKNOWN')
    log.info("Browsing %s using '%s'..." % (url, browser_name))
    return browser.open(url)


def main(path, interface="localhost", port=8080):
    try:
        docroot = os.path.realpath(path)
        globals()['DOCUMENTROOT'] = docroot
        server = get_webserver(interface=interface, port=port,
                               handler=DocrootHandler)
        log.info('Starting httpserver...')
        log.info('Document_root = %s' % docroot)
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
