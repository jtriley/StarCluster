import os
import gzip
import StringIO

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from starcluster import exception

starts_with_mappings = {
    '#include': 'text/x-include-url',
    '#!': 'text/x-shellscript',
    '#cloud-config': 'text/cloud-config',
    '#cloud-config-archive': 'text/cloud-config-archive',
    '#upstart-job': 'text/upstart-job',
    '#part-handler': 'text/part-handler',
    '#cloud-boothook': 'text/cloud-boothook',
    '#sc-store': 'text/sc-store'
}

sc_part_handler = """\
#part-handler
def list_types():
    return(["text/sc-store"])
def handle_part(data, ctype, filename, payload):
    pass
"""

def get_type(fp):
    line = fp.readline()
    fp.seek(0)
    # slist is sorted longest first
    slist = starts_with_mappings.keys()
    slist.sort(key=lambda e: -1 * len(e))
    for sstr in slist:
        if line.startswith(sstr):
            return starts_with_mappings[sstr]
    raise exception.BaseException("invalid user data type")


def mp_userdata_from_strings(strings, compress=False):
    files = [StringIO.StringIO(s) for s in strings]
    return mp_userdata_from_files(files, compress=compress)


def mp_userdata_from_files(files, compress=False):
    outer = MIMEMultipart()
    for i, fp in enumerate(files):
        mtype = get_type(fp)
        maintype, subtype = mtype.split('/', 1)
        if maintype == 'text':
            # Note: we should handle calculating the charset
            msg = MIMEText(fp.read(), _subtype=subtype)
            fp.close()
        else:
            fp = open(fp.name, 'rb')
            msg = MIMEBase(maintype, subtype)
            msg.set_payload(fp.read())
            fp.close()
            # Encode the payload using Base64
            encoders.encode_base64(msg)
        # Set the filename parameter
        msg.add_header('Content-Disposition', 'attachment',
                       filename=os.path.basename(getattr(fp, 'name', str(i))))
        outer.attach(msg)
    userdata = outer.as_string()
    if compress:
        s = StringIO.StringIO()
        gfile = gzip.GzipFile(fileobj=s, mode='w')
        gfile.write(userdata)
        gfile.close()
        s.seek(0)
        userdata = s.read()
    return userdata
