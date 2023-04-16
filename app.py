import requests
from bs4 import BeautifulSoup
import configparser
import datetime
import requiredUnits
import requiredClass
import reqLocations
from sortedcontainers import SortedDict
import smtplib
import os
import re

dir_path = os.path.dirname(os.path.realpath(__file__))

configFile = os.path.join(dir_path, 'config.ini')
config = configparser.ConfigParser()
config.read(configFile)

outfile = os.path.join(dir_path, config['files']['outfile'])
logFile = os.path.join(dir_path, config['files']['logFile'])

debug = config.getboolean('general','debug')
printMsg = config.getboolean('general','printMsg')

runLocation = config['general']['location']
lineEnd = ''
if runLocation == 'local':
  lineEnd = '\r'
else:
  lineEnd = '\n'

baseUrl = config['website']['baseUrl']
userAgent = config['website']['userAgent']
userAgentHdr = {'User-agent': userAgent}

fromTime = config['website']['fromTime']
toTime = config['website']['toTime']
timeSpan = fromTime + '-' + toTime


reqUnits = requiredUnits.all
reqClass = requiredClass.all
locations = reqLocations.all

startTime = datetime.datetime.now().strftime("%H:%M:%S")

total = 0

lFile = open(logFile, "a")


def main():

  log('Script Starts')
  unitServDict = SortedDict()
  reqDate = datetime.date.today().strftime("%Y-%m-%d")

  for location in locations.keys():

    tocs = locations[location]
    for toc in tocs:

      services = getServices(location, toc, reqDate, timeSpan)

      for service in services:
        units, serviceDet = checkService2(service, reqUnits)
        for unit in units:
          if unit in unitServDict:
            allServices = unitServDict[unit]
            if allServices.count(serviceDet) == 0:
              allServices.append(serviceDet)
          else:
            allServices = [serviceDet]

          unitServDict[unit] = allServices

  printReqUnitServ(unitServDict, reqDate)

  log('Script Ends')
  lFile.close()

   

def getServices(location, toc, reqDate, reqTime):

  if toc == 'ALL':  
    templateUrl = '/search/detailed/{}/{}/{}?stp=WVS&show=all&order=wtt'
    urlSufix = templateUrl.format(location, reqDate, reqTime)
  else:
    templateUrl = '/search/detailed/{}/{}/{}?stp=WVS&show=all&order=wtt&toc={}'
    urlSufix = templateUrl.format(location, reqDate, reqTime, toc)
  
  url = baseUrl + urlSufix
  page = requests.get(url, headers = userAgentHdr)  
  soup = BeautifulSoup(page.text, 'html.parser')
  

  serviceUrls = []

  for row in soup.findAll('a', attrs = {'class':'service'}):
    
    serviceUrl = row.attrs['href']
    serviceUrls.append(serviceUrl)

  return serviceUrls


def checkService(serviceUrl, reqUnits):
  url = baseUrl + serviceUrl
  page = requests.get(url, headers = userAgentHdr)  
  soup = BeautifulSoup(page.text, 'html.parser')

  units = []

  for row in soup.find_all("span", class_="identity"):
    unitID = row.getText().strip()
    
    if reqClass.count(unitID[:3]) > 0:
      units.append(unitID)
    elif reqClass.count(unitID[:2]) > 0:
      units.append(unitID)
    elif reqUnits.count(unitID) > 0:
      #if units.count(unitID) == 0:
      units.append(unitID)

  serviceDetails = soup.find("div", class_="header").getText().strip()

  return(units, serviceDetails)
  
def checkService2(serviceUrl, reqUnits):
  url = baseUrl + serviceUrl
  page = requests.get(url, headers = userAgentHdr)  
  soup = BeautifulSoup(page.text, 'html.parser')

  units = []

  alloc = soup.find("div", class_="allocation")

  if alloc is not None:
    theText = alloc.getText()
    
    numbers = re.findall('[0-9]+', theText)

    for unitID in numbers:
    
      if reqClass.count(unitID[:3]) > 0:
        units.append(unitID)
      elif reqClass.count(unitID[:2]) > 0:
        units.append(unitID)
      elif reqUnits.count(unitID) > 0:
        #if units.count(unitID) == 0:
        units.append(unitID)

  serviceDetails = soup.find("div", class_="header").getText().strip()

  return(units, serviceDetails)

def printReqUnitServ(unitServDict, reqDate):

  oFile = open(outfile, "w")
  emailBody =''

  #theTime = datetime.datetime.now().strftime("%H:%M:%S")
  oFile.write(f"Allocations for {reqDate} at {startTime}\r")
  oFile.write(" \r")
  emailBody = emailBody + f"Allocations for {reqDate} at {startTime}\r\n"
  emailBody = emailBody + "\r\n"
  emailSubject = f"Allocations for {reqDate} at {startTime}"

  total = 0
  for key in unitServDict:
    if reqUnits.count(key) > 0:
      oFile.write(key + '*\r')
      emailBody = emailBody + key + "*\r\n"
    else:
      oFile.write(key + '\r')
      emailBody = emailBody + key + "\r\n"
    total = total + 1
    allTheServices = unitServDict[key]
    for eachService in allTheServices:
      oFile.write(eachService + '\r')
      emailBody = emailBody + eachService + "\r\n"
    oFile.write(" \r")
    emailBody = emailBody + "\r\n"
  
  log(f'Total numbers of units working today : {total}')
  oFile.write(f'Total numbers of units working today : {total}\r')
  emailBody = emailBody + f'Total numbers of units working today : {total}\r\n'

  oFile.close()

  sendEmail(emailSubject, emailBody)


def sendEmail(subject, body):

  email_user = config['email']['emailUser']
  email_pword = config['email']['emailPw']
  to = config['email']['emailTo']
  email_server = config['email']['emailServer']

  #log('Password is {}'.format(email_pword), 1)

  try:
    server = smtplib.SMTP_SSL(email_server, 465)
    server.ehlo()
    server.login(email_user, email_pword)

    message = 'Subject: {}\n\n{}'.format(subject, body)
    server.sendmail(email_user, to, message.encode('utf8'))
    server.quit()

    log('Email sent OK')

  except Exception as ex:
    log('Error sending email')
    log(str(ex))


def log(msg, debugInd=0):
  
  isDebug = bool(debugInd)

  if not(isDebug) or (isDebug and debug):
    lFile.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f") + ' ' + msg + lineEnd)
    if printMsg:
      print(msg)



main()
