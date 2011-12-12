#!/usr/bin/python
import os
import os.path as path
import subprocess
import re

"""
    Routes failover script
"""

''' Must be of the form : 'default via <ip> dev <if>' '''
favoritegw = 'default via 192.168.1.1 dev eth0'
via_re = re.compile('default via (.*) dev (\w+)\s*(metric \d+)?')

def getroutes():
    global via_re
    p = subprocess.Popen(['/bin/ip', 'route'], stdout=subprocess.PIPE)
    for line in p.stdout:
        line = line.strip()
        match = via_re.match(line)
        if match is not None:
            yield line

def pingroute(ip):
    p = subprocess.Popen(['/bin/ping', '-i', '0.5', '-W', '0.75', '-q', '-n', '-c', '1', ip], stdout=subprocess.PIPE)
    if p.wait() != 0:
        return False
    return True

def setroute(route, metric=None):
    global conffilepath
    global via_re
    p = None
    groups = via_re.match(route).groups()
    cmd = ['/bin/ip', 'route', 'replace', 'default', 'via', groups[0], 'dev', groups[1]]
    if metric is not None:
        cmd.append('metric')
        cmd.append(str(metric))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    if p.wait() != 0:
        print >> sys.stderr, "Error: route can't be replaced"
        return False
    return True

if __name__=="__main__":
    favoritegroups = via_re.match(favoritegw).groups()
    routes = []
    currentgw = None
    changed = False
    for route in getroutes():
        groups = via_re.match(route).groups()
        if groups[0] == favoritegroups[0] and groups[1] == favoritegroups[1]:
            ''' Favorite gateway must be the first in the list of routes '''
            routes.insert(0, route)
            if groups[2] is None:
                currentgw = route
        else:
            if groups[2] is None:
                currentgw = route
            else:
                routes.append(route)
    routes.insert(1, currentgw) # in order to have (favoritegw, currentgw, others...)
    currentgwgroups = via_re.match(currentgw).groups()
    for route in routes:
        groups = via_re.match(route).groups()
        if not changed and pingroute(groups[0]):
            if groups[0] != currentgwgroups[0] or groups[1] != currentgwgroups[1]:
                ''' Ping and is not in use, so use it ! '''
                setroute(route)
                changed = True
                print 'route "%s" is now in use !' % route
            else:
                break
        else:
            if groups[0] == currentgwgroups[0] and groups[1] == currentgwgroups[1]:
                if not changed:
                    print 'route "%s" is dead :/' % route
                setroute(route, 10)

