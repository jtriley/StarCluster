#!/usr/bin/python2.4
import platform
import os, pickle

print '>>> Recovering config pickle'
file = open('/mnt/config.pkl', 'r')
config_dict = pickle.load(file)
file.close()
os.system('rm -f /mnt/config.pkl')

print '>>> Protecting ami from private data...'
os.system('find /home -maxdepth 1 -type d -exec rm -rf {}/.ssh \;') #remove all user's .ssh dir
os.system('rm -rf ~/.ssh/*')
os.system('rm -f /var/log/secure')
os.system('rm -f /var/log/lastlog')
os.system('rm -rf /root/*')
os.system('rm -f ~/.bash_history')
os.system('rm -rf /tmp/*')

# get arch option for ec2-bundle-vol
arch = platform.architecture()[0]
if arch == "32bit":
    arch = "i386"
elif arch == "64bit":
    arch = "x86_64"
else: 
    arch = "i386"
config_dict['arch'] = arch

# perform the bundle
print '>>> Beginning the bundle process: '
os.system('ec2-bundle-vol -d /mnt -k /mnt/%(private_key)s -c /mnt/%(cert)s -p %(prefix)s -u %(userid)s -r %(arch)s' % config_dict)

# upload bundle to S3
print '>>> Uploading the bundle image: '
os.system('ec2-upload-bundle -b %(bucket)s -m /mnt/%(prefix)s.manifest.xml -a %(access_key)s -s %(secret_key)s' % config_dict)

print '>>> Cleaning up...'
# delte keys and remove bash history
os.system('rm -f /mnt/pk-*.pem /mnt/cert-*.pem')
os.system('rm -f ~/.bash_history')
