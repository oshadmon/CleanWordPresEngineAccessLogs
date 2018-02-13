"""
By: Ori Shadmon 
Date: December 2017 
Description: The following piece of code takes the "Access Log" files from WP Engine, and retirves the following 
- IP Address(es) and how frequently they visited 
- Dates in which they visited 
""" 

import datetime
import googlemaps
import os
from pygeocoder import Geocoder
import re 
import requests
import sys 

class Main: 
   def __init__(self, *args): 
      """
      The following class controls the process by which everything runs
      :args: 
         args  (sys.argv):list - Valules declared when calling test (shown in _help method)
      """
      if "--help" in sys.argv: 
         self._help()
      self._declare_values(values=sys.argv)

   def _help(self, invalid:str=""):
      """
      Print options to screen and exit
      :args: 
         invalid:str - If the user wants an option that isn't supported, then a corresponding error is printed 
      """ 
      if invalid is not "":
         print("Exception - '%s' is not supported\n" % str(invalid))
      print("Option List: "
           +"\n\t--file: log file containing relevent information [--file=$HOME/tmp/site_logs.txt]"
           +"\n\t--api-key: Google's API key to use Google Maps API [--api-key=aaaBcD123kd-d83c-C83s]"
           +"\n\t--query: The type of location to check [--query=lunch]"
           +"\n\t--radius: In meters how far from source to check [--radius=0]"
           +"\n\t--timestamp:  Print a list the accessed timestamps per IP. If set to False (default), then print only the number of times that IP accessed the website"
           ) 
      exit(1)

   def _declare_values(self, values:list=[]): 
      """
      Declare values that are used through the program
      :args:
         file:str - File logs file containing relevent information
         api_key:str - Google's API key to use Google Maps API (https://developers.google.com/maps/documentation/javascript/get-api-key)
         query:str - The type of location to check.
         radius:str - In meters how far from source to check 
         timestamp:boolean - Print a list the accessed timestamps per IP. If set to False (default), then print only the number of times
	                     that IP accessed the website
      """
      self.file = "$HOME/tmp/site_logs.txt"
      self.api_key = "aaaBcD123kd-d83c-C83s"
      self.query = "lunch" 
      self.radius = 0
      self.timestamp = False
      for value in values: 
         if value is sys.argv[0]: 
            pass 
         elif "--file" in value: 
            self.file = value.split("=")[-1]
         elif "--api-key" in value: 
            self.api_key = value.split("=")[-1]
         elif "--query" in value: 
            self.query = value.split("=")[-1]
         elif "--radius" in value: 
            self.radius = int(value.split("=")[-1]) 
         elif "--timestamp" in value: 
            self.timestamp = True
         else: 
            self._help(invalid=value)
      self.file = self.file.replace("$HOME", os.getenv("HOME")).replace("$PWD", os.getenv("PWD")).replace("~", os.path.expanduser('~'))
       
   def print_data(self, data:dict={}): 
      for ip in data:  
         if self.timestamp is True: 
            output ="%s -\n\tCoordiantes: %s\n\tFrequency: %s\n\tTimestamps: %s\n\tAddress: %s\n\tNear By Places: %s" 
            output = output % (ip, data[ip]['coordinates'], len(data[ip]["timestamp"]), data[ip]["timestamp"], data[ip]["address"], data[ip]["owner"])
            print(output)  
         else: 
            output ="%s -\n\tCoordinates, \n\tFrequency: %s\n\tAddress: %s\n\tNear By Places: %s"        
            output = output % (ip, data[ip]['coordinates'], len(data[ip]["timestamp"]), data[ip]["address"], data[ip]["owner"]) 
            print(output)


   def main(self): 
      iff = InfoFromFile(file=self.file) 
      data = iff.itterate_file()
      for ip in data:
         li = LocationInfo(ip=ip, api_key=self.api_key, query=self.query, radius=self.radius)
         lat, long = li._get_lat_long()
         coordinates = "(%s, %s)" % (str(lat), str(long))
         address = li._get_address(lat, long)
         owners = li._get_possible_owners(lat, long, self.query)
         if self.timestamp is True: 
            output = "%s -\n\tFrequency: %s\n\tTimestamp: %s\n\tCoordinates: %s\n\tAddress: %s\n\tPlaces: %s"
            print(output % (ip, len(data[ip]["timestamp"]), data[ip]["timestamp"], coordinates, address, owners))
         else: 
            output = "%s -\n\tFrequency: %s\n\tCoordinates: %s\n\tAddress: %s\n\tPlaces: %s"
            print(output % (ip, len(data[ip]["timestamp"]), coordinates, address, owners))

class InfoFromFile: 
   def __init__(self, file:str="$HOME/tmp/s3_file.txt"): 
      """
      The following class takes a file, and retrives the IP and access timestamps
      from it. 
      :args: 
         file:str - file containing lines of relevent data
      """    
      self.f = file 
      self.data = {}

   def itterate_file(self)->dict: 
      """
      Itterate through a file containing relevent information
      :return:
         return dict containing IPs and their corresponding timestamps
      """
      f = open(self.f, 'r')
      for line in f.readlines(): 
         ip = self._get_ip(line)
         timestamp = self._get_timestamp(line)
         if ip in self.data and timestamp not in self.data[ip]: 
            self.data[ip]["timestamp"].append(self._get_timestamp(line))
         elif ip not in self.data: 
            self.data[ip]={"timestamp":[self._get_timestamp(line)]}
      f.close()
      return self.data 

   def _get_ip(self, line:str="")->str: 
      """
      Retrive IP address from line
      :args:
         line containing IP address
      :return: 
         the derived IP address
      """
      IPPattern = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
      return re.findall(IPPattern, line)[0]

   def _get_timestamp(self, line:str="")->str:
      """
      Retrive timestamp from line 
      :args:
         line containing timestamp
      :return:
         the derived timestamp
      """
      original_date = line.split("[")[-1].split("]")[0].split(" +")[0].split(":",1)[0]
      original_time = line.split("[")[-1].split("]")[0].split(" +")[0].split(":",1)[-1]
      try:
         timestamp = datetime.datetime.strptime(original_date, "%d/%b/%Y").strftime("%Y-%m-%d")
      except ValueException:
         return(original_date + " " + original_time)
      else:
         return(timestamp + " " + original_time)

class LocationInfo: 
   def __init__(self, ip:str='127.0.0.1', api_key:str='aaabbbcccdddeee1112_123fg', query:str='lunch', radius:int=0): 
      """
      The following class, takes an IP address, and then using Google's API generates a rough calculation of which
      places accessed the site. This is done using a query (specify the type of location), and radius (how far from the
      source should the system check). Note that the radius is in Meters. 
      :args: 
         ip:str - the IP address that accessed the site
         gmaps:str - Google's API key to use Google Maps API (https://developers.google.com/maps/documentation/javascript/get-api-key)
         query: str - The type of location to check. 
         radius:int - In meters how far from source to check  
      """
      self.ip = ip
      self.gmaps = googlemaps.Client(key=api_key)
      self.query = query 
      self.radius = radius

   def _get_lat_long(self) -> (float, float): 
      """
      This function connects to the FreeGeoIP web service to get info from IP addresses.
      Returns two latitude and longitude.
      Code from: https://github.com/pieqq/PyGeoIpMap/blob/master/pygeoipmap.py
      :args:
         long:float - correspnds to the longitutude
         lat:float - corresponds to the latitude 
      :return:
         Return the address and lat/long of each IP accesseing dianomic
         if there is an error then code returns lat/long
      """
      lat = 0.0
      long = 0.0
      r = requests.get("https://freegeoip.net/json/" + self.ip)
      json_response = r.json()
      if json_response['latitude'] and json_response['longitude']:
         lat = json_response['latitude']
         long = json_response['longitude']
      return lat, long

   def _get_address(self, lat:float=0.0, long:float=0.0) -> str: 
      """
      Based on the latitude and longitutde, generate address
      :return:
         return address:str
      """
      try: 
         address = self.gmaps.reverse_geocode((lat, long))
      except googlemaps.exceptions._RetriableRequest: 
         return "Failed to get Address due to API Key limit. For more info: https://developers.google.com/maps/documentation/javascript/get-api-key" 
      except googlemaps.exceptions.Timeout: 
         return "Failed to get Address due to API Key timeout. For more info: https://developers.google.com/maps/documentation/javascript/get-api-key"
      else: 
         return address[0]['formatted_address']

   def _get_possible_owners(self, lat:float=0.0, long:float=0.0, query:str="lunch") -> str:
      """
      Generate a list of places based on the lcation, query, and radius (in meters)
      :args: 
         query:str - what the user is searching for
      :return:
         "list" of potential places based on query 
      """
      result = ""
      try: 
         places = self.gmaps.places(query=self.query, location=(lat, long), radius=self.radius)
      except googlemaps.exceptions as e: 
         return "Failed to get potential %s places due to API Key limit. For more info: https://developers.google.com/maps/documentation/javascript/get-api-key" % query
      except ooglemaps.exceptions.Timeout:
         return "Failed to get potential %s places due to API Key timeout. For more info: https://developers.google.com/maps/documentation/javascript/get-api-key" % query 
      else: 
         for dict in places['results']:
            result += dict['name'] + ", "
         return result


if __name__ == "__main__": 
   m = Main() 
   m.main()
