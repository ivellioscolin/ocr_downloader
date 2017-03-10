#!/usr/bin/python
import shutil
import json
import os
import sys
import errno
from threading import Thread

try:
    from urllib.request import urlopen, Request
    from html.parser import HTMLParser
except ImportError:
    from urllib2 import urlopen, Request
    from HTMLParser import HTMLParser

ocDownloadUrl = 'https://www3.oculus.com/en-us/setup/'
ocInstallerConfigUrl = 'https://graph.oculus.com/bootstrap_installer_config'
ocSetupName = 'OculusSetup.exe'
ocDownloadCachePath = 'c:\\OculusSetup-DownloadCache'
ocAccessToken = 'access_token=OC|1582076955407037|'
ocUserAgent = 'Oculus/Dawn {"1.10.0.310422"}'
chromeUserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'

class SetupLinkParser(HTMLParser):
    def __init__(self):
        self.url = ''
        HTMLParser.__init__(self)
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            ocSetupFound = 0
            for name,value in attrs:
                if name == 'id' and value == 'rift-setup-download-button-link':
                    ocSetupFound = 1
                    break
            if ocSetupFound == 1:
                for name,value in attrs:
                    if name == 'href':
                        self.url = value
                        break
    def getUrl(self):
        return self.url

def AddAccessToken(url):
    urlWToken = url
    if(url.find('?') == -1):
        urlWToken = url+'?'+ocAccessToken
    else:
        urlWToken = url+'&&'+ocAccessToken
    return urlWToken

def RequestInstaller():
    req = Request(AddAccessToken(ocDownloadUrl))
    req.add_header('User-agent', chromeUserAgent)
    reqRes = urlopen(req)
    return reqRes.read().strip().decode('utf-8')

def RequestInstallerConfig():
    req = Request(AddAccessToken(ocInstallerConfigUrl))
    req.add_header('User-agent', ocUserAgent)
    reqRes = urlopen(req)
    installerConfigJson = json.loads(reqRes.read().strip().decode('utf-8'))
    return installerConfigJson

def DownloadFileThread(uri, loc, fileName, size):
    okToDownload = 0
    if(not os.path.exists(loc)):
        try:
            os.makedirs(loc)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
    if(os.path.exists(loc)):
        fullName = loc
        if loc[-1] != '\\':
            fullName += '\\'
        fullName += fileName
        if(os.path.isfile(fullName)):
            statinfo = os.stat(fullName)
            if size != statinfo.st_size or size == 0:
                okToDownload = 1
        else:
            okToDownload = 1
    if okToDownload == 1:
        print ('Download %s' %(fileName))
        fp = urlopen(AddAccessToken(uri)) 
        fd = fp.read() 
        with open(fullName, "wb") as raw:
            raw.write(fd)
    else:
        print ('Skip %s' %(fileName))

def DownloadManager():
    tList = []

    print ('********************')
    print ('Start downloading...')

    # Parse main setup
    url = SetupLinkParser()
    url.feed(RequestInstaller())
    th = Thread(target = DownloadFileThread, kwargs={'uri': url.getUrl(), 'loc': os.path.dirname(os.path.realpath(__file__)), 'fileName' : ocSetupName, 'size' : 0})
    th.start()
    tList.append(th)

    # Parse applications
    instCfg = RequestInstallerConfig()
    for item in instCfg['applications']:
        th = Thread(target = DownloadFileThread, kwargs={'uri': item['uri'], 'loc': ocDownloadCachePath, 'fileName' : item['canonical_name']+'.zip', 'size' : int(item['packed'])})
        th.start()
        tList.append(th)

    # Parse redistributables
    for item in instCfg['redistributables']:
        th = Thread(target = DownloadFileThread, kwargs={'uri': item['uri'], 'loc': ocDownloadCachePath, 'fileName' : item['canonical_name']+'.exe', 'size' : int(item['size'])})
        th.start()
        tList.append(th)

    # Parse video
    th = Thread(target = DownloadFileThread, kwargs={'uri': instCfg['video']['uri'], 'loc': ocDownloadCachePath, 'fileName' : 'teaser.wmv', 'size' : int(instCfg['video']['size'])})
    th.start()
    tList.append(th)

    for th in tList:
        th.join()

    print ('Download finish.')
    print ('********************')

def InstallManager():
    setupFile = os.path.dirname(os.path.realpath(__file__))+'\\'+ocSetupName
    if(os.path.isfile(setupFile)):
        print ('Run %s...' %(setupFile))
        os.system(setupFile)
    else:
        print ("Can't find %s" %(setupFile))

def Usage():
    print ('Oculus Setup Helper')
    print ('Usage:')
    print ('Download only: python OculusDownload.py d')
    print ('Install only: python OculusDownload.py i')
    print ('Download & Install: python OculusDownload.py di')

if __name__ == '__main__':
    validArg = 0
    if len(sys.argv) == 2:
        if sys.argv[1] == 'd':
            DownloadManager()
            validArg = 1
        elif sys.argv[1] == 'i':
            InstallManager()
            validArg = 1
        elif sys.argv[1] == 'di':
            DownloadManager()
            InstallManager()
            validArg = 1
        else:
            validArg = 0

    if validArg == 0:
        Usage()

