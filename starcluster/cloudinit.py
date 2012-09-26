import os
import gzip
import email
import StringIO

from email import encoders
from email.mime import base
from email.mime import text
from email.mime import multipart

from starcluster import exception

starts_with_mappings = {
    '#include': 'text/x-include-url',
    '#!': 'text/x-shellscript',
    '#cloud-config': 'text/cloud-config',
    '#cloud-config-archive': 'text/cloud-config-archive',
    '#upstart-job': 'text/upstart-job',
    '#part-handler': 'text/part-handler',
    '#cloud-boothook': 'text/cloud-boothook',
    '#ignored': 'text/ignore'
}


def _get_type_from_fp(fp):
    line = fp.readline()
    fp.seek(0)
    # slist is sorted longest first
    slist = starts_with_mappings.keys()
    slist.sort(key=lambda e: -1 * len(e))
    for sstr in slist:
        if line.startswith(sstr):
            return starts_with_mappings[sstr]
    raise exception.BaseException("invalid user data type: %s" % line)


def mp_userdata_from_strings(strings, compress=False):
    files = [StringIO.StringIO(s) for s in strings]
    return mp_userdata_from_files(files, compress=compress)


def mp_userdata_from_files(files, compress=False):
    outer = multipart.MIMEMultipart()
    mtypes = []
    for i, fp in enumerate(files):
        mtype = _get_type_from_fp(fp)
        mtypes.append(mtype)
        maintype, subtype = mtype.split('/', 1)
        if maintype == 'text':
            # Note: we should handle calculating the charset
            msg = text.MIMEText(fp.read(), _subtype=subtype)
            fp.close()
        else:
            if hasattr(fp, 'name'):
                fp = open(fp.name, 'rb')
            msg = base.MIMEBase(maintype, subtype)
            msg.set_payload(fp.read())
            fp.close()
            # Encode the payload using Base64
            encoders.encode_base64(msg)
        # Set the filename parameter
        fname = getattr(fp, 'name', "sc_%d" % i)
        msg.add_header('Content-Disposition', 'attachment',
                       filename=os.path.basename(fname))
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


def get_mp_from_userdata(userdata, decompress=False):
    if decompress:
        zfile = StringIO.StringIO(userdata)
        gfile = gzip.GzipFile(fileobj=zfile, mode='r')
        userdata = gfile.read()
        gfile.close()
    return email.message_from_string(userdata)
