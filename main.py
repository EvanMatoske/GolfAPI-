#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import webapp2
from google.appengine.ext import ndb
import json
import datetime
from google.appengine.ext import db
import os
from google.appengine.ext.webapp import template
import urllib
from google.appengine.api import urlfetch
import string
from urlparse import urlparse
from googleapiclient import discovery
import httplib2
from oauth2client import client
import logging
urlfetch.set_default_fetch_deadline(45)

class Round(ndb.Model):
    player = ndb.StringProperty()
    date = ndb.StringProperty()
    score = ndb.IntegerProperty()
    location = ndb.StringProperty()
    weather = ndb.StringProperty()
    id = ndb.StringProperty()

class Course(ndb.Model):
    name = ndb.StringProperty()
    address = ndb.StringProperty()
    city = ndb.StringProperty()
    state = ndb.StringProperty()
    zip = ndb.StringProperty()
    id = ndb.StringProperty()



class MainHandler(webapp2.RequestHandler):

    def get(self):
       self.response.write('Hello World')


#This Handler handles all requests pertaining to Rounds
class RoundHandler(webapp2.RequestHandler):

    #Add a round
    def post(self):
        #Openweather api key
        APPID = '9857ee26442e0d907dde6cd08a567b35'

        #Loads access token for google and gets google email
        credentials = self.request.authorization[1]
        player = userInfo(credentials)

        #Load the request info
        round_info = json.loads(self.request.body)

        #Load the JSON file provided from openweather to search for city id to use in request
        city_list = json.load(open("city.list.json"))
        location = round_info['location']
        city_id = None
        for city in city_list:
            if city['name'] == location:
                city_id = city['id']
                city_id = str(city_id)
                #self.response.write(city_id)
                break
        if city_id is None:
            self.response.write('City does not exist')

        #Makes request to openweather with location provided from user
        url = 'http://api.openweathermap.org/data/2.5/weather'
        data1 = {}
        data2 = {}
        data1['id'] = city_id
        data2['APPID'] = APPID
        param1 = urllib.urlencode(data1)
        param2 = urllib.urlencode(data2)
        url = url + '?' + param1 + '&' + param2
        info = urlfetch.fetch(
            url=url,
            method=urlfetch.GET,
            )
        weather = json.loads(info.content)


        #Create new round and add information and put in datastore
        round_weather = weather['weather'][0]['description']
        new_round = Round(player=player, score=round_info['score'])
        new_round.put()
        new_round.id = str(new_round.key.urlsafe())
        new_round.location = location
        new_round.weather = round_weather
        new_round.date = str(datetime.datetime.now())
        new_round.put()

        #Respond to the user with the information that was loaded to the datastore
        self.response.write(json.dumps(new_round.to_dict(),indent=4,separators=(',',':')))

    #Gets round specific to the user
    def get(self):

        credentials = self.request.authorization[1]
        player = userInfo(credentials)
        player_rounds = json.dumps([r.to_dict() for r in Round.query(Round.player == player).fetch()],indent=4,separators=(',',':'))
        self.response.write(player_rounds)

    #Delete round using the rounds ID provided by the user
    def delete(self, roundID):

        round_key = ndb.Key(urlsafe=roundID)
        if round_key.get() == None:
            self.response.write('Invalid ID')
        else:
            round = round_key.get()
            round.key.delete()
            self.response.write('Round deleted!')

    #Update round info
    def put(self, roundID):
        round_key = ndb.Key(urlsafe=roundID)
        if round_key.get() == None:
            self.response.write('Invalid ID')
        else:
            round_data = json.loads(self.request.body)
            round = round_key.get()
            round.score = round_data['score']
            round.put()
            round_dict = round.to_dict()
            self.response.write(json.dumps(round_dict, indent=4, separators=(',', ':')))



#This Handler handles all requests pertaining to Courses
class CourseHandler(webapp2.RequestHandler):
    def post(self):

        #Add new score to datastore
        course_info = json.loads(self.request.body)
        new_course = Course(
            name=course_info['name'],
            address=course_info['address'],
            city=course_info['city'],
            state=course_info['state'],
            zip=course_info['zip']
        )
        new_course.put()
        new_course.id = str(new_course.key.urlsafe())
        new_course.put()
        course_dict = new_course.to_dict()
        course_dict['self'] = '/course/'+ new_course.key.urlsafe()
        self.response.write(json.dumps(new_course.to_dict(), indent=4, separators=(',', ':')))

    #Get all the courses in the datastore
    def get(self):
        for courses in Course.query():
            self.response.write(json.dumps(courses.to_dict(),indent=4,separators=(',',':')))

    #Delete course by ID
    def delete(self, courseID):
        course_key = ndb.Key(urlsafe=courseID)
        if course_key.get == None:
            self.response.write('Invalid Course')
        else:
            course = course_key.get()
            course.key.delete()
            self.response.write('Course deleted!')

    def put(self, courseID):
        course_key = ndb.Key(urlsafe=courseID)
        course = course_key.get()
        if course_key.get == None:
            self.response.write('Invalid Course')
        else:
            course_data = json.loads(self.request.body)
            course.address = course_data['address']
            course.name = course_data['name']
            course.city = course_data['city']
            course.state = course_data['state']
            course.zip = course_data['zip']
            course.put()
            course_dict = course.to_dict()
            self.response.write(json.dumps(course_dict,indent=4,separators=(',',':')))



#Function to make a call to google API to get a users email
#Takes a users Access Token and returns the users email address
def userInfo(token):

    credentials = token
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    url = 'https://www.googleapis.com/plus/v1/people/me'
    url = url + '?access_token=' + credentials
    info = urlfetch.fetch(
        url=url,
        method=urlfetch.GET,
        headers=headers,
    )

    response = json.loads(info.content)
    results = response['emails'][0]['value']
    return results



app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/round', RoundHandler),
    ('/round/([A-z0-9\-]+)', RoundHandler),
    ('/course', CourseHandler),
    ('/course/([A-z0-9\-]+)', CourseHandler),



], debug=True)
