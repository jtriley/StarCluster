import xml.dom.minidom
import re
import string

def qacct_to_datetime_tuple(qacct):
    """
    Takes the SGE qacct formatted time and makes a datetime tuple
    format is:
    Tue Jul 13 16:24:03 2010
    """
    return datetime.datetime.strptime(qacct, "%a %b %d %H:%M:%S %Y")


def parse_qhost(strval,qname=None):
    """
    this function parses qhost -xml output and makes a neat array
    takes in a string, so we can pipe in output from ssh.exec('qhost -xml')
    """
    hosts = []  # clear the old hosts
    doc = xml.dom.minidom.parseString(strval)
    for h in doc.getElementsByTagName("host"):
        queues = [q.getAttribute('name') for q in h.getElementsByTagName("queue")]
        if qname is None or qname in queues:
            name = h.getAttribute("name")
            hash = {"name": name, 'queues':queues}
            for stat in h.getElementsByTagName("hostvalue"):
                for hvalue in stat.childNodes:
                    attr = stat.attributes['name'].value
                    val = ""
                    if hvalue.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                        val = hvalue.data
                    hash[attr] = val
            if hash['name'] != u'global':
                hosts.append(hash)
    return hosts
    
DEFAULT_QSTAT_FIELDS = ["JB_job_number", "state", "JB_submission_time",
                       "queue_name", "slots", "tasks"]  
def parse_qstat(strval,fields=None):
    """
    This method parses qstat -xml output and makes a neat array
    """
    if fields == None:
        fields = DEFAULT_QSTAT_FIELDS
    jobs = []  # clear the old jobs
    doc = xml.dom.minidom.parseString(strval)
    for job in doc.getElementsByTagName("job_list"):
        jstate = job.getAttribute("state")
        hash = {"job_state": jstate}
        for tag in fields:
            es = job.getElementsByTagName(tag)
            for node in es:
                for node2 in node.childNodes:
                    if node2.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                        hash[tag] = node2.data
        # grab the submit time on all jobs, the last job's val stays
        jobs.append(hash)
    return jobs


def parse_qacct(strval, dtnow):
    """
    This method parses qacct -j output and makes a neat array and
    calculates some statistics.
    Takes the string to parse, and a datetime object of the remote
    host's current time.
    """
    job_id = None
    qd = None
    start = None
    end = None
    counter = 0
    lines = strval.split('\n')
    jobstats = {}
    for l in lines:
        l = l.strip()
        if l.find('jobnumber') != -1:
            job_id = int(l[13:len(l)])
        if l.find('qsub_time') != -1:
                qd = qacct_to_datetime_tuple(l[13:len(l)])
        if l.find('start_time') != -1:
                if l.find('-/-') > 0:
                    start = dtnow
                else:
                    start = qacct_to_datetime_tuple(l[13:len(l)])
        if l.find('end_time') != -1:
                if l.find('-/-') > 0:
                    end = dtnow
                else:
                    end = qacct_to_datetime_tuple(l[13:len(l)])
        if l.find('==========') != -1:
            if qd != None:
                hash = {'queued': qd, 'start': start, 'end': end}
                jobstats[jobid] = hash
            qd = None
            start = None
            end = None
            counter = counter + 1
    
    return jobstats,counter

def get_queues(sge_host):
    return sge_host.ssh.execute('source /etc/profile && qconf -sql', log_output=False)

def get_hosts(sge_host,qname=None):
    qhost_cmd = 'source /etc/profile && qhost -xml -q' 
    qhostxml = '\n'.join(sge_host.ssh.execute(qhost_cmd, log_output=False))
    parsed_xml = parse_qhost(qhostxml,qname=qname)
    return dict([(h.pop('name'),h) for h in parsed_xml])
    
def get_host_groups(sge_host):
    q_pattern = re.compile("([\S]+)[\s]+(.*)")
    hg_data = sge_host.ssh.execute('source /etc/profile && qconf -shgrpl', log_output=False)
    host_groups = []
    for hg in hg_data:
        output = '\n'.join(sge_host.ssh.execute('source /etc/profile && qconf -shgrp ' + hg,log_output=False))           
        parsed_output = dict([x.groups() for x in list(q_pattern.finditer(output))])
        parsed_output['hostlist'] = parsed_output['hostlist'].split(' ')
        host_groups.append(parsed_output)
    return dict([(h.pop('group_name'),h) for h in host_groups])
        
def add_queue(sge_host,qname):
    tmpfile = '/tmp/qconf_' + qname
    F = sge_host.ssh.remote_file(tmpfile,'w')
    s = string.Template(QCONF_TEMPLATE).substitute({"QNAME":qname})
    F.write(s)
    F.close()
    return sge_host.ssh.execute('source /etc/profile && qconf -Aq ' + tmpfile)

def create_queue(sge_host,qname):
    existing_queues = get_queues(sge_host)
    if not qname in existing_queues:
        return add_queue(sge_host,qname)
            
def add_host_group(sge_host,hgname):
    tmpfile = '/tmp/hgconf_' + hgname
    F = sge_host.ssh.remote_file(tmpfile,'w')
    s = string.Template(HGCONF_TEMPLATE).substitute({"HGNAME":hgname})
    F.write(s)
    F.close()
    return sge_host.ssh.execute('source /etc/profile && qconf -Ahgrp ' + tmpfile)        
    
def create_host_group(sge_host,hgname):
    existing_hostgroups = get_host_groups(sge_host)
    if not hgname in existing_hostgroups:
        return add_host_group(sge_host,hgname)


def get_num_procs(node):
    #should we use this instead of the method implemented in SGEStats object?
    #or use that one instead of this? 
    tmpfile = '/tmp/numcpus'
    node.ssh.execute(
         'su - root -c "(cat /proc/cpuinfo | grep processor | wc -l) > ' + tmpfile + '"')
    output = int(node.ssh.remote_file(tmpfile,'r').read().strip())
    return output


def add_to_queue(sge_host,qname,names):
    q_pattern = re.compile("([\S]+)([\s]+)(.*)")
    output = '\n'.join(sge_host.ssh.execute('source /etc/profile && qconf -sq ' + qname,log_output=False))
    parsed_output = [x.groups() for x in list(q_pattern.finditer(output))]
    slot_pattern = re.compile('\[([\S]+)=[\d]+\]')

    for (ind,(k,_s,v)) in enumerate(parsed_output):
        if k == 'hostlist':
            if v == 'NONE':
                newv = ' '.join(names)
            else:
                existing_hosts = v.split(' ')
                to_add = filter(lambda x : x not in existing_hosts,names)
                newv = v + ' ' + ' '.join(to_add)   
            parsed_output[ind] = (k,_s,newv)

    new_conf_string = '\n'.join([k + _s + v for (k,_s,v) in parsed_output])

    tmpfile = '/tmp/qmod_' + qname
    F = sge_host.ssh.remote_file(tmpfile ,'w')
    F.write(new_conf_string)
    F.close()
    return sge_host.ssh.execute('source /etc/profile && qconf -Mq ' + tmpfile)


def add_to_queue_with_slots(sge_host,qname,aliases,slots):

    if isinstance(slots,dict):
        slotdict = slots
    else:
        slotdict = dict([(alias,slots) for alias in aliases])
    
    q_pattern = re.compile("([\S]+)([\s]+)(.*)")
    output = '\n'.join(sge_host.ssh.execute('source /etc/profile && qconf -sq ' + qname,log_output=False))
    parsed_output = [x.groups() for x in list(q_pattern.finditer(output))]
    slot_pattern = re.compile('\[([\S]+)=[\d]+\]')

    for (ind,(k,_s,v)) in enumerate(parsed_output):
        if k == 'hostlist':
            if v == 'NONE':
                newv = ' '.join(aliases)
            else:
                existing_hosts = v.split(' ')
                to_add = filter(lambda x : x not in existing_hosts,aliases)
                newv = v + ' ' + ' '.join(to_add)
            parsed_output[ind] = (k,_s,newv)
        elif k == 'slots':
            existing_hosts = [_match.groups()[0] for _match in list(slot_pattern.finditer(v))]
            to_add = filter(lambda x : x not in existing_hosts,aliases)
            slotstring = ['[' + _a + '=' + str(slotdict[_a]) + ']' for _a in to_add]
            newv = v + ',' + ','.join(slotstring)
            parsed_output[ind] = (k,_s,newv)                            
    new_conf_string = '\n'.join([k + _s + v for (k,_s,v) in parsed_output])
    
    tmpfile = '/tmp/qmod_' + qname
    F = sge_host.ssh.remote_file(tmpfile ,'w')
    F.write(new_conf_string)
    F.close()
    return sge_host.ssh.execute('source /etc/profile && qconf -Mq ' + tmpfile)
    
    
def add_slots_to_queue(sge_host,qname,aliases,slots):

    if isinstance(slots,dict):
        slotdict = slots
    else:
        slotdict = dict([(alias,slots) for alias in aliases])

    q_pattern = re.compile("([\S]+)([\s]+)(.*)")
    output = '\n'.join(sge_host.ssh.execute('source /etc/profile && qconf -sq ' + qname,log_output=False))
    parsed_output = [x.groups() for x in list(q_pattern.finditer(output))]
    slot_pattern = re.compile('\[([\S]+)=[\d]+\]')

    for (ind,(k,_s,v)) in enumerate(parsed_output):
        if k == 'slots':
            existing_hosts = [_match.groups()[0] for _match in list(slot_pattern.finditer(v))]
            to_add = filter(lambda x : x not in existing_hosts,aliases)
            slotstring = ['[' + _a + '=' + str(slotdict[_a]) + ']' for _a in to_add]
            newv = v + ',' + ','.join(slotstring)
            parsed_output[ind] = (k,_s,newv)
                                
    new_conf_string = '\n'.join([k + _s + v for (k,_s,v) in parsed_output])
    tmpfile = '/tmp/qmod_' + qname
    F = sge_host.ssh.remote_file(tmpfile ,'w')
    F.write(new_conf_string)
    F.close()
    return sge_host.ssh.execute('source /etc/profile && qconf -Mq ' + tmpfile)
    
    
def add_to_host_group(sge_host,hgname,aliases):
    output = '\n'.join(sge_host.ssh.execute('source /etc/profile && qconf -shgrp ' + hgname,log_output=False))
    q_pattern = re.compile("([\S]+)[\s]+(.*)")
    parsed_output = [x.groups() for x in list(q_pattern.finditer(output))]
    
    for (i,(k,v)) in enumerate(parsed_output):
        if k == 'hostlist':
            if v == 'NONE':
                newv =' '.join(aliases)
            else:
                existing_hosts = v.split(' ')
                to_add = filter(lambda x : x not in existing_hosts,aliases)
                newv = v + ' ' + ' '.join(to_add)
            parsed_output[i] = (k,newv)
                                
    new_conf_string = '\n'.join([k + ' ' + v for (k,v) in parsed_output])
    tmpfile = '/tmp/hgmod_' + hgname
    F = sge_host.ssh.remote_file(tmpfile ,'w')
    F.write(new_conf_string)
    F.close()
    return sge_host.ssh.execute('source /etc/profile && qconf -Mhgrp ' + tmpfile)


def remove_from_queue(sge_host,qname,aliases):

    contents = '\n'.join(sge_host.ssh.execute(
        'source /etc/profile && qconf -sq ' + qname, log_output = False))    
    q_pattern = re.compile("([\S]+)([\s]+)(.*)")
    parsed_output = [x.groups() for x in list(q_pattern.finditer(contents))]

    for (i,(k,s,v)) in enumerate(parsed_output):
        if k == 'hostlist':
            vlist = v.split(' ')
            for alias in aliases:
                if alias in vlist:
                    vlist.remove(alias)
            if vlist:
                newv = ' '.join(vlist)
            else:
                newv = 'NONE'
            parsed_output[i] = (k,s,newv)
        elif k == 'slots':
            newv = v
            for alias in aliases:
                regex = re.compile(r"\[%s=\d+\],?" % alias)
                newv = regex.sub('',newv).strip(',').replace(',,',',')
            parsed_output[i] = (k,s,newv)
            
    new_conf_string = '\n'.join([k + s + v for (k,s,v) in parsed_output])
    
    tmpfile = '/tmp/qmod_' + qname      
    f = sge_host.ssh.remote_file(tmpfile, 'w')    
    f.write(new_conf_string)
    f.close()
    return sge_host.ssh.execute('source /etc/profile && qconf -Mq ' + tmpfile)


def remove_from_sge(sge_host,alias):

	#find all queues the node is     
	#remove the node and its slots from each queue
	hosts = get_hosts(sge_host)
	for qname in hosts[alias]['queues']:
	    remove_from_queue(sge_host,qname,[alias])

	#get all host groups the node is in
	#remove it from all the host groups
	host_groups = get_host_groups(sge_host)
	for (hgname,hg) in host_groups.items():
		if alias in hg['hostlist']:
			remove_from_host_group(sge_host,hgname,[alias])	  
	 
	#remove host configuration
	sge_host.ssh.execute(
		'source /etc/profile && qconf -de %s' % alias)
	sge_host.ssh.execute(
		'source /etc/profile && qconf -dconf %s' % alias)
		
		

QCONF_TEMPLATE = """qname                 $QNAME
hostlist              NONE
seq_no                0
load_thresholds       np_load_avg=1.75
suspend_thresholds    NONE
nsuspend              1
suspend_interval      00:05:00
priority              0
min_cpu_interval      00:05:00
processors            UNDEFINED
qtype                 BATCH INTERACTIVE
ckpt_list             NONE
pe_list               make orte
rerun                 FALSE
slots                 1
tmpdir                /tmp
shell                 /bin/bash
prolog                NONE
epilog                NONE
shell_start_mode      posix_compliant
starter_method        NONE
suspend_method        NONE
resume_method         NONE
terminate_method      NONE
notify                00:00:60
owner_list            NONE
user_lists            NONE
xuser_lists           NONE
subordinate_list      NONE
complex_values        NONE
projects              NONE
xprojects             NONE
calendar              NONE
initial_state         default
s_rt                  INFINITY
h_rt                  INFINITY
s_cpu                 INFINITY
h_cpu                 INFINITY
s_fsize               INFINITY
h_fsize               INFINITY
s_data                INFINITY
h_data                INFINITY
s_stack               INFINITY
h_stack               INFINITY
s_core                INFINITY
h_core                INFINITY
s_rss                 INFINITY
h_rss                 INFINITY
s_vmem                INFINITY
h_vmem                INFINITY
"""

HGCONF_TEMPLATE = """group_name $HGNAME
hostlist NONE
"""

import BeautifulSoup
def get_qstat(sge_host,queue_name):

    output_all = '\n'.join(sge_host.ssh.execute('source /etc/profile && qstat -xml',log_output=False))
    parsed_output = parse_qstat(output_all)
    
    jobs = [str(j.contents[0]) for j in BeautifulSoup.BeautifulStoneSoup(output_all).findAll('jb_job_number')]
    queue_jobs = []
    for j in jobs:
        output = '\n'.join(sge_host.ssh.execute('source /etc/profile && qstat -xml -j ' + j,log_output=False))
        Soup = BeautifulSoup.BeautifulStoneSoup(output)
        qname = Soup.findAll(lambda x : x.name == 'ce_name' and x.text == 'qname')[0].findNext('ce_stringval').text
        if qname == queue_name:
            queue_jobs.append(j)
    
    return [p for p in parsed_output if p['JB_job_number'] in queue_jobs]
        
