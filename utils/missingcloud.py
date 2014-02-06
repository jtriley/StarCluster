import sys
import time
import json
import urllib2
import traceback

from BeautifulSoup import BeautifulSoup as bs

from starcluster import config


class MissingCloud(object):

    ITYPES_HTML_URL = "http://aws.amazon.com/ec2/instance-types/"
    LINUX_OD_JSON = " http://aws.amazon.com/ec2/pricing/json/linux-od.json"
    DEFAULT_REGION = "us-east-1"
    HVM_AMI = "ami-52a0c53b"
    NON_HVM_AMI = "ami-765b3e1f"
    SPOT_BID = "0.80"

    def __init__(self):
        self._ec2 = None
        self._itypes_html = None
        self._linux_od_json = None
        self._itypes = None
        self._region_types_map = None
        self._hvm_types = None
        self._hvm_only_types = None
        self._placement_group_regions = None
        self._placement_group_types = None

    def fetch(self):
        print self.INSTANCE_TYPES
        print self.REGION_TYPES_MAP
        print self.PLACEMENT_GROUP_TYPES
        print self.PLACEMENT_GROUP_REGIONS
        print self.HVM_ONLY_TYPES
        print self.HVM_TYPES

    def dump(self):
        pass

    @property
    def ec2(self):
        if not self._ec2:
            cfg = config.StarClusterConfig().load()
            self._ec2 = cfg.get_easy_ec2()
        return self._ec2

    @property
    def html(self):
        if not self._itypes_html:
            f = urllib2.urlopen(self.ITYPES_HTML_URL)
            self._itypes_html = bs(f.read())
            f.close()
        return self._itypes_html

    @property
    def json(self):
        if not self._linux_od_json:
            f = urllib2.urlopen(self.LINUX_OD_JSON)
            self._linux_od_json = json.loads(f.read())
            f.close()
        return self._linux_od_json

    @property
    def REGION_TYPES_MAP(self):
        if not self._region_types_map:
            self._region_types_map = self._get_regions_to_types_map()
        return self._region_types_map

    @property
    def INSTANCE_TYPES(self):
        if not self._itypes:
            self._itypes = {}
            itypes_tab = self._get_tables()[0]
            for itype in itypes_tab[1:]:
                _arch_map = {'64-bit': 'x86_64', '32-bit': 'i386'}
                arches = [_arch_map[a.strip()] for a in itype[2].split('or')]
                self._itypes[itype[1]] = arches
        return self._itypes

    @property
    def PLACEMENT_GROUP_TYPES(self):
        if not self._placement_group_types:
            itypes_tab = self._get_tables()[0]
            pgtypes = []
            for itype in itypes_tab[1:]:
                if '10 Gigabit4' in itype:
                    pgtypes.append(itype[1])
            self._placement_group_types = pgtypes
        return self._placement_group_types

    @property
    def PLACEMENT_GROUP_REGIONS(self):
        if not self._placement_group_regions:
            self._placement_group_regions = self._get_placement_group_regions()
        return self._placement_group_regions

    @property
    def HVM_TYPES(self):
        if not self._hvm_types:
            self._hvm_types = self._get_hvm_types()
        return self._hvm_types

    @property
    def HVM_ONLY_TYPES(self):
        if not self._hvm_only_types:
            self._hvm_only_types = self._get_hvm_only_types()
        return self._hvm_only_types

    def show_types_by_region(self, region_types_map):
        header = '*' * 80
        for region in region_types_map:
            print header
            print region
            print header
            counter = 0
            itypes = region_types_map[region]
            for itype in itypes:
                print itype
                counter += 1
            print 'Total = %d\n' % counter

    def _get_regions_to_types_map(self):
        regions = self.json['config']['regions']
        m = {}
        for r in regions:
            i_types = []
            m[r['region']] = i_types
            itypes = r['instanceTypes']
            for it in itypes:
                sizes = it['sizes']
                for s in sizes:
                    i_types.append(s['size'])
        return m

    def __table_to_list(self, table):
        result = []
        allrows = table.findAll('tr')
        for row in allrows:
            result.append([])
            allcols = row.findAll('td')
            for col in allcols:
                thestrings = [unicode(s) for s in col.findAll(text=True)]
                thetext = ''.join(thestrings)
                result[-1].append(thetext.strip())
        return result

    def _get_tables(self):
        tables = []
        for table in self.html.findAll('table'):
            tables.append(self.__table_to_list(table))
        return tables

    def _get_placement_group_regions(self):
        regions = self.ec2.regions
        pgregions = []
        for region in regions:
            self.ec2.connect_to_region(region)
            try:
                pg = self.ec2.create_placement_group('tester')
                time.sleep(5)
                pg.delete()
                pgregions.append(region)
            except Exception:
                print "Region %s does not support placement groups" % region
                traceback.print_exc(file=sys.stdout)
        return pgregions

    def _get_hvm_types(self):
        self.ec2.connect_to_region(self.DEFAULT_REGION)
        hvm_types = []
        for itype in self.INSTANCE_TYPES:
            try:
                r = self.ec2.request_instances(self.HVM_AMI,
                                               price=self.SPOT_BID,
                                               instance_type=itype,
                                               security_groups=['default'])
                self.ec2.wait_for_propagation(spot_requests=r)
                for s in r:
                    s.cancel()
                print "Instance type '%s' supports HVM!" % itype
                hvm_types.append(itype)
            except:
                print "Instance type '%s' does not support HVM" % itype
                traceback.print_exc(file=sys.stdout)
        return hvm_types

    def _get_hvm_only_types(self):
        self.ec2.connect_to_region(self.DEFAULT_REGION)
        hvm_only_types = []
        for itype in self.HVM_TYPES:
            try:
                r = self.ec2.request_instances(self.NON_HVM_AMI,
                                               price=self.SPOT_BID,
                                               instance_type=itype,
                                               security_groups=['default'])
                self.ec2.wait_for_propagation(spot_requests=r)
                for s in r:
                    s.cancel()
                print "Instance type '%s' supports both HVM and NON-HVM!" % itype
            except:
                print "Instance type '%s' ONLY supports HVM" % itype
                traceback.print_exc(file=sys.stdout)
                hvm_only_types.append(itype)
        return hvm_only_types


def main():
    MissingCloud().fetch()

if __name__ == '__main__':
    main()


