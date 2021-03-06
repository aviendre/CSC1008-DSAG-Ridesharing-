from onemapsg import OneMapClient
from datetime import datetime
import sys
import math
import djikstra as d
import pandas as pd
import graph as g

# Woh Hup, Energizer, Sin sin, Toll City, JTC, Amos Supply
postalCode = ['629215', '629197', '629541', '628509', '629637', '629613']
poi = [
    'GUL CIRCLE MRT STATION (EW30)', 'GUL CIRCLE DISTRICENTRE', 'GUL STREET 2',
    '19 GUL LANE', '126 GUL CIRCLE', '24249 (BUS STOP)', '24229 (BUS STOP)'
]

#Initialization
Client = OneMapClient("ridhwanproper@gmail.com", "esMrbzVsFr")

graph = pd.read_csv('distance.csv', header=0, index_col=0).squeeze().to_dict()
graph = d.initGraph(graph)

#.get(intersection No.)
# 0 - longitude
# 1 - latitude
intersectionNodes = g.GraphNode()

#starting = Client.get_planning_area_bounds()
driverList = []
customerList = []

MAXRADIUS = 0.4


class Customer:
    ''' Customer class to encompass the variables: \n
    ... \n
    Attributes: \n
        name:string, unique name identifier \n
        capacity:int, amount of riders in one transaction \n
        start_point:list, [lat,long] coordinates of the customer \n
        end_point:list, [lat,long] coordinates of the destination \n
        shared:boolean, True if shared service, False if solo service
    '''
    def __init__(self, name, capacity, start_point, end_point, shared):
        self.name = name
        self.capacity = capacity
        self.start_point = start_point
        self.end_point = end_point
        self.shared = shared
        self.soloPicked = False

    def getName(self):
        return self.name

    def isShared(self):
        return self.shared

    def getCapacity(self):
        return self.capacity

    def getPickup(self):
        return self.start_point

    def getDropoff(self):
        return self.end_point

    def soloPicked(self):
        return self.soloPicked


class Driver:
    ''' Driver class to encompass the variables: \n
    ... \n
    Attributes: \n
        name:string, unique name identifier \n
        capacity:int, amoung of riders in one transaction \n
        currentLocation:list, [lat,long] coordinates of the customer \n
        shared:boolean, True if shared service, False if solo service \n
        sharedCounter:int, current transaction counter for shared service \n
        sharedPassenger:List<Customer>, customer objects stored \n
        pickupLocation: [lat,long] coordinates of the pickup location \n
        dropoffLocation: [lat,long] coordinates of the dropoff location \n
    '''
    def __init__(self, name, currentLocation, capacity, shared):
        self.name = name
        self.capacity = capacity
        self.currentLocation = currentLocation
        self.shared = shared
        self.sharedCounter = 0
        self.sharedPassenger = []
        self.pickupLocation = ''
        self.dropoffLocation = ''
        self.soloPicked = False

    def soloPicked(self):
        return self.soloPicked

    def setSharedPattern(self, x):
        self.sharedRoute = x

    def getSharedPattern(self):
        return self.sharedRoute

    def storeSharedPassenger(self, cust):
        self.increaseSharedCounter()
        self.sharedPassenger.append(cust)

    def getPassengers(self):
        return self.sharedPassenger

    def increaseSharedCounter(self):
        self.sharedCounter += 1

    def getSharedCounter(self):
        return self.sharedCounter

    def resetSharedCounter(self):
        self.sharedCounter = 0

    def getName(self):
        return self.name

    def isShared(self):
        return self.shared

    def getCurrentLocation(self):
        return self.currentLocation

    def getCapacity(self):
        return self.capacity

    def minusCapacity(self, amount):
        self.capacity -= amount

    def getPickup(self):
        return self.pickupLocation

    def getDropoff(self):
        return self.dropoffLocation

    def setRoute(self, *args):
        self.route = args

    def getRoute(self):
        return self.route

    def setPickup(self, location):
        self.pickupLocation = location

    def setDropoff(self, location):
        self.dropoffLocation = location

    def toString(self):
        return ('isShared(): ' + str(self.shared) + '\nCurrent Location: ' +
                str(self.currentLocation) + '\nPickup Location: ' +
                str(self.pickupLocation) + '\nDrop-off Location: ' +
                str(self.dropoffLocation))

    def distAwayFromCust(self, customer):
        return g.calculateDist(float(self.getCurrentLocation()[0]),
                               float(self.getCurrentLocation()[1]),
                               float(customer.getPickup()[0]),
                               float(customer.getPickup()[1]))


#Driver is the object to reference to
# x is the current location nearest node
# y is the pickup location nearest node
# z is the dropoff location nearest node
def calculateJourney(driver, x, y, z):
    '''(Solo Service)Gets the route from the driver current location -> pickup location -> dropoff Location \n
    Formats the output to be passed into the OneMap API call \n
    ... \n
    Parameters \n
        driver:Driver, current driver object to get route \n
        x:int, nearest node to driver current location \n
        y:int, nearest node to driver pickup location \n
        z:int, nearest node to driver dropoff location \n
    ...
    Returns \n
        string - routes of the journey from driver current location -> pickup location -> dropoff Location
        integer - total time taken for the whole journey
    '''
    #initialization of the route
    route = '['
    route += str(driver.getCurrentLocation()) + ','

    # Current location to pickup location (Driver Start Route)
    root = d.dijkstra(graph, x, y)
    routeToPickup,dist = d.generatePath(root, y)
    for i in routeToPickup:
        route += str((intersectionNodes.get(
            int(i))[1], intersectionNodes.get(int(i))[0])) + ','
    route += str(driver.getPickup()) + ','
    
    #Pickup location to Endpoint location (Route)
    root = d.dijkstra(graph, y, z)
    pickupToEndpoint,temp = d.generatePath(root, z)
    for i in pickupToEndpoint:
        route += str((intersectionNodes.get(
            int(i))[1], intersectionNodes.get(int(i))[0])) + ','
    route += str(driver.getDropoff())
    dist += temp
    
    #Formatting of the string to easily pass to the OneMap API
    route += ']:255,0,0:3'
    route = route.replace(' ', '')
    route = route.replace('(', '[')
    route = route.replace(')', ']')
    route = route.replace("'", '')
  
    return route, dist


def calculateJourneyShared(driver, q, w, x, y, z):
    '''(Shared Service) Gets the route from the driver current location -> 2 pickup location -> 2 dropoff Location \n
    Formats the output to be passed into the OneMap API call \n
    ... \n
    Parameters \n
        driver:Driver, current driver object to get route \n
        q:int, nearest node to driver current location \n
        w:int, nearest node to driver pickup location 1 \n
        x:int, nearest node to driver pickup location 2 \n
        y:int, nearest node to driver dropoff location 1 \n
        z:int, nearest node to driver dropoff location 2 \n
    ...
    Returns \n
        string - routes of the journey from driver current location -> 2 pickup location -> 2 dropoff Location
        integer - total time taken for the whole journey
    '''
    route = '['
    route += str(driver.getCurrentLocation()) + ','

    # Current location to 1st pickup location (Driver Start Route q -> w)
    root = d.dijkstra(graph, q, w)
    routeToPickup,dist = d.generatePath(root, w)
    for i in routeToPickup:
        route += str((intersectionNodes.get(
            int(i))[1], intersectionNodes.get(int(i))[0])) + ','
    route += str(driver.getPassengers()[int(
        driver.getSharedPattern().split(',')[0])].getPickup()) + ','

    # 1st pickup location to 2nd pickup location (w -> x)
    root = d.dijkstra(graph, w, x)
    routeToPickup,temp = d.generatePath(root, x)
    for i in routeToPickup:
        route += str((intersectionNodes.get(
            int(i))[1], intersectionNodes.get(int(i))[0])) + ','
    route += str(driver.getPassengers()[int(
        driver.getSharedPattern().split(',')[1])].getPickup()) + ','
    dist += temp

    #Pickup location to 1st Drop off location (x -> y)
    root = d.dijkstra(graph, x, y)
    pickupToEndpoint,temp = d.generatePath(root, y)
    for i in pickupToEndpoint:
        route += str((intersectionNodes.get(
            int(i))[1], intersectionNodes.get(int(i))[0])) + ','
    route += str(driver.getPassengers()[int(
        driver.getSharedPattern().split(',')[2])].getDropoff()) + ','
    dist += temp

    #1st Drop off Location to 2nd Drop off location (y -> z)
    root = d.dijkstra(graph, y, z)
    pickupToEndpoint, temp = d.generatePath(root, z)
    for i in pickupToEndpoint:
        route += str((intersectionNodes.get(
            int(i))[1], intersectionNodes.get(int(i))[0])) + ','
    route += str(driver.getPassengers()[int(
        driver.getSharedPattern().split(',')[3])].getDropoff())
    dist += temp

    #Formatting of the route to be passed to the OneMap API
    route += ']:255,0,0:3'
    route = route.replace(' ', '')
    route = route.replace('(', '[')
    route = route.replace(')', ']')
    route = route.replace("'", '')
    
    return route, dist


def calculatePoints(driver):
    '''(Solo Service) Gets the points of all stopping points in the journey \n
    Formats the output to be passed into the OneMap API call \n
    ... \n
    Parameters \n
        driver:Driver, current driver object to get route \n
    ...
    Returns \n
        string - returns the points of all stopping points
    '''
    points = str(driver.getCurrentLocation())
    points = points.replace(')', ',"255,178,0","A"]')
    points = points.replace(')', ']')
    points += '|'
    points += str(driver.getPickup())
    points = points.replace(')', ',"255,178,0","B"]')
    points += '|'
    points += str(driver.getDropoff())
    points = points.replace(')', ',"255,178,0","C"]')
    points = points.replace('(', '[')
    points = points.replace(' ', '')
    points = points.replace("'", '')
    return points


def calculateSharedPoints(driver):
    '''(Shared Service) Gets the points of all stopping points in the journey \n
    Formats the output to be passed into the OneMap API call \n
    ... \n
    Parameters \n
        driver:Driver, current driver object to get route \n
    ...
      Returns \n
          string - returns the points of all stopping points
    '''

    colorCodes = ["180,0,0","0,180,0","0,0,180"]

    string = (',"' + colorCodes[2]+'","A"]')
    points = str(driver.getCurrentLocation())
    points = points.replace(')', string)
    points = points.replace(')', ']')
    points += '|'
    points += str(driver.getPassengers()[int(
        driver.getSharedPattern().split(',')[0])].getPickup())
    
    string = (',"' + colorCodes[int(driver.getSharedPattern().split(',')[0])]+'","B"]')
    points = points.replace(')', string)
    points += '|'
    points += str(driver.getPassengers()[int(
        driver.getSharedPattern().split(',')[1])].getPickup())
    string = (',"' + colorCodes[int(driver.getSharedPattern().split(',')[1])]+'","C"]')
    points = points.replace(')', string)
    points += '|'
    points += str(driver.getPassengers()[int(
        driver.getSharedPattern().split(',')[2])].getDropoff())
    string = (',"' + colorCodes[int(driver.getSharedPattern().split(',')[2])]+'","D"]')
    points = points.replace(')', string)
    points += '|'
    points += str(driver.getPassengers()[int(
        driver.getSharedPattern().split(',')[3])].getDropoff())
    string = (',"' + colorCodes[int(driver.getSharedPattern().split(',')[3])]+'","E"]')
    points = points.replace(')', string)
    points = points.replace('(', '[')
    points = points.replace(' ', '')
    points = points.replace("'", '')
    return points


#x1 is the latitude
#x2 is the longitude
def nearestNode(x1, x2):
    '''Retrieves the nearest nodes between the given [lat,long] and all intersections \n
    ... \n
    Parameters \n
        x1:float, latitude of point \n
        x2:float. longitude of point \n
    ...
    Returns \n
        string - intersection number of the nearest node
    '''
    min = g.calculateDist(x1, x2,
                          intersectionNodes.get(1)[1],
                          intersectionNodes.get(1)[0])
    nearest = 1
    for i in range(2, len(intersectionNodes)):
        temp = g.calculateDist(x1, x2,
                               intersectionNodes.get(i)[1],
                               intersectionNodes.get(i)[0])
        if temp < min:
            min = temp
            nearest = i
    return str(nearest)


def soloMatching(customer, dri):
    '''(Solo Service) Does all the necessary routing to act as a GPS service \n
    ... \n
    Parameters \n
        customer:Customer, current customer object to get pickup and dropoff coordinates \n
        driver:Driver, current driver object to get route \n
    ...
    Returns \n
        list - [route to be taken by driver, stopping points of route]
    '''
    dri.setPickup(customer.getPickup())
    dri.setDropoff(customer.getDropoff())

    x = nearestNode(float(dri.getCurrentLocation()[0]),
                    float(dri.getCurrentLocation()[1]))
    y = nearestNode(float(dri.getPickup()[0]), float(dri.getPickup()[1]))
    z = nearestNode(float(dri.getDropoff()[0]), float(dri.getDropoff()[1]))

    route, dist = calculateJourney(dri, x, y, z)
    cost, time, distance = calculateJourneyDetails(dist, 'Solo')
    return (route,
            calculatePoints(dri),
            cost,
            time,
            distance,
            customer.getName())


def sharedMatching(dri):
    '''(Shared Service) Does all the necessary routing to act as a GPS service \n
    ... \n
    Parameters \n
        driver:Driver, current driver object to get route \n
    ...
    Returns \n
        list - [route to be taken by driver, stopping points of route]
    '''
    list = dri.getPassengers()
    P1 = list[0].getPickup()
    P2 = list[1].getPickup()
    D1 = list[0].getDropoff()
    D2 = list[1].getDropoff()
    cl = dri.getCurrentLocation()

    clToP1 = g.calculateDist(float(cl[0]), float(cl[1]), float(P1[0]),
                             float(P1[1]))
    clToP2 = g.calculateDist(float(cl[0]), float(cl[1]), float(P2[0]),
                             float(P2[1]))

    #p1ToD1 = g.calculateDist(float(P1[0]),float(P1[1]),float(D1[0]),float(D1[1]))
    #p1ToD2 = g.calculateDist(float(P1[0]),float(P1[1]),float(D2[0]),float(D2[1]))

    p2ToD1 = g.calculateDist(float(P2[0]), float(P2[1]), float(D1[0]),
                             float(D1[1]))
    p2ToD2 = g.calculateDist(float(P2[0]), float(P2[1]), float(D2[0]),
                             float(D2[1]))

    clNode = nearestNode(float(cl[0]), float(cl[1]))
    p1Node = nearestNode(float(P1[0]), float(P1[1]))
    p2Node = nearestNode(float(P2[0]), float(P2[1]))
    d1Node = nearestNode(float(D1[0]), float(D1[1]))
    d2Node = nearestNode(float(D2[0]), float(D2[1]))

    if (clToP1 > clToP2):
        if (p2ToD1 > p2ToD2):
            #cl -> p2 -> p1 -> d2 -> d1 
            dri.setSharedPattern('1,0,1,0')
            q, w, x, y, z = clNode, p2Node, p1Node, d2Node, d1Node
        else:
            #cl -> p2 -> p1 -> d1 -> d2
            dri.setSharedPattern('1,0,0,1')
            q, w, x, y, z = clNode, p2Node, p1Node, d1Node, d2Node
    else:
        if (p2ToD1 > p2ToD2):
            #cl -> p1 -> p2 -> d2 -> d1
            dri.setSharedPattern('0,1,1,0')
            q, w, x, y, z = clNode, p1Node, p2Node, d2Node, d1Node
        else:
            #cl -> p1 -> p2 -> d1 -> d2
            dri.setSharedPattern('0,1,0,1')
            q, w, x, y, z = clNode, p1Node, p2Node, d1Node, d2Node
    #(routes),(points) refer to calculateJourney,calculatePoints
    route,dist = calculateJourneyShared(dri, q, w, x, y, z)
    cost, time, distance = calculateJourneyDetails(dist, 'Shared')
    return (route
            ,calculateSharedPoints(dri)
            ,cost
            ,time
            ,distance
            ,dri.getPassengers()[0].getName()
            ,dri.getPassengers()[1].getName())


def UserToDriver(customerList, driverList):
    '''Program call to handle all of the matching of the customers to their drivers \n
    ... \n
    Parameters \n
        customerList:List, list of all customer objects \n
        driverList:List, list of all driver objects \n
    ...
    Returns \n
        Dict - [driver's name : [route to be taken by driver, stopping points of route]]
    '''
    global MAXDISTANCE
    soloDriver = []
    sharedDriver = []
    currentMatching = {}

    #Stores the drivers into their services provided to cut processing time
    for i in driverList:
        if i.isShared():
            sharedDriver.append(i)
        else:
            soloDriver.append(i)

    #iterate through the whole customer list
    for cust in customerList:
        #Check for the service requested by the user
        if not cust.isShared():
            nDriver = soloDriver[0]
            nDriverDist = soloDriver[0].distAwayFromCust(cust)

            #print("\n==[List of drivers / KM aways]== (Solo)")
            for i in range(0, len(soloDriver)):
                
                if(soloDriver[i].soloPicked):         
                        nDriver = soloDriver[i+1]
                        nDriverDist = soloDriver[i+1].distAwayFromCust(cust)
                # Check whether driver is indeed nearest to customer :)
                #print(soloDriver[i].name, soloDriver[i].distAwayFromCust(cust), soloDriver[i].getCapacity())
                if (soloDriver[i].getCapacity() >= cust.getCapacity()):
                    # right now nDriverDist is set to 0
                    # what if 0 cant fit. how will it affect the if below
                  if soloDriver[i].distAwayFromCust(cust) < nDriverDist and not soloDriver[i].soloPicked:
                      nDriverDist = soloDriver[i].distAwayFromCust(cust)
                      nDriver = soloDriver[i]
                      continue
                  #print("\n")
                else:
                  continue
            #print(nDriver.getName(), cust.getName())

            if (nDriver.getCapacity() >= cust.getCapacity()) and (nDriver.soloPicked == False and cust.soloPicked == False):
                currentMatching[nDriver.getName()] = soloMatching(
                    cust, nDriver)
                cust.soloPicked = True
                nDriver.soloPicked = True
            else:
                continue

        #Check for the service requested by the user
        elif cust.isShared():
            #reset all distances from customer to driver
            allDistances = []
            nDriver = sharedDriver[0]
            nDriverDist = sharedDriver[0].distAwayFromCust(cust)

            for i in range(0, len(sharedDriver)):
                #if there is 2 drivers which meet this condition, it will minus both the drivers since both meet the conditions.
                #there is no unique condition to check if the user can accept drivers or not
              if (sharedDriver[i].getSharedCounter() == 2
                        or sharedDriver[i].getCapacity() < cust.getCapacity()):
                    allDistances.append(sys.maxsize)
              else:
                  allDistances.append(sharedDriver[i].distAwayFromCust(cust))

            #append the customer with the shortest distance to the driver
            sharedDriver[allDistances.index(min(allDistances))].storeSharedPassenger(cust)
            sharedDriver[allDistances.index(min(allDistances))].minusCapacity(cust.getCapacity())
            
            
    for i in sharedDriver:
        if i.getSharedCounter() == 2:
            currentMatching[i.getName()] = sharedMatching(i)
        elif i.getSharedCounter() == 1:
            currentMatching[i.getName()] = soloMatching(i.getPassengers()[0],i)
    return currentMatching

def calculateJourneyDetails(distance, service):
  SPEED = 50 #km/h
  now = datetime.now()
  currentHour = now.strftime("%H")
  now = datetime.now()
  currentDay = now.strftime("%A")
  peakPeriod = [7,8,9,17,18,19,20]
  peakDays = ['Friday, Saturday, Sunday']
  basePrice = 5
  peakPrice = 3.5
  hourMultiplier = 1
  dayMultiplier = 0
  gst = 1.07
  serviceMultiplier = 1
  pickUpTime = 2.5
  
  if (service == 'Shared'):
    serviceMultiplier = 0.7
    pickUpTime *= 2
  if (currentDay in peakDays):
    dayMultiplier = 1
  if (int(currentHour) in peakPeriod):
    hourMultiplier = 1.5
  
  cost = (serviceMultiplier * hourMultiplier * (math.floor(distance)+basePrice+(peakPrice*dayMultiplier)) * gst)
          
  time = (distance / SPEED) * 60 + pickUpTime
  
  return "$"+"{:.2f}".format(round(cost,1)), str(math.ceil(time))+" minutes", str(round(distance,2))+" km"
    
      

    

#Driver List Shared service
driver1 = Client.search('628509').get('results')
driver1data = next(iter(driver1))
driverList.append(
    Driver('Ben', (driver1data.get('LATITUDE'), driver1data.get('LONGITUDE')),
           4, True))
driver1 = Client.search('629621').get('results')
driver1data = next(iter(driver1))
driverList.append(
    Driver('Troy', (driver1data.get('LATITUDE'), driver1data.get('LONGITUDE')),
           6, True))

#Driver List Solo Service
driver2 = Client.search('629545').get('results')
driver2data = next(iter(driver2))
driverList.append(
    Driver('Carl', (driver2data.get('LATITUDE'), driver2data.get('LONGITUDE')),
           6, False))
driver3 = Client.search('629613').get('results')
driver3data = next(iter(driver3))
driverList.append(
    Driver('Arif', (driver3data.get('LATITUDE'), driver3data.get('LONGITUDE')),
           4, False))
driver4 = Client.search('629545').get('results')
driver4data = next(iter(driver4))
driverList.append(
    Driver('Denzel',
           (driver4data.get('LATITUDE'), driver4data.get('LONGITUDE')), 2,
           False))
# print(UserToDriver(customerList, driverList))
