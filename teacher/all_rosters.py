import os
import urllib
import jinja2
import webapp2
import logging
import json

import models
import authorizer
import logic

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(os.path.dirname(__file__))),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

dayOrder = ['Mon A', 'Mon B', 'Tues A', 'Tues B',
            'Thurs A', 'Thurs B', 'Fri A', 'Fri B']

def listOrder(c):
  if 'instructor' in c:
    return (c['name'],
            c['instructor'],
            dayOrder.index(c['schedule'][0]['daypart']))
  else:
    return (c['name'],
            dayOrder.index(c['schedule'][0]['daypart']))

class AllRosters(webapp2.RequestHandler):
  def get(self):
    auth = authorizer.Authorizer(self)
    if not auth.HasTeacherAccess():
      auth.Redirect()
      return

    institution = self.request.get("institution")
    if not institution:
      logging.fatal("no institution")
    session = self.request.get("session")
    if not session:
      logging.fatal("no session")

    message = self.request.get('message')
    session_query = urllib.urlencode({'institution': institution,
                                      'session': session})
    email = auth.teacher_email

    classes = models.Classes.FetchJson(institution, session)
    if classes:
      classes.sort(key=listOrder)

    template_values = {
      'institution' : institution,
      'session' : session,
      'message': message,
      'session_query': session_query,
      'teacher': auth.teacher_entity,
      'classes': classes,
    }
    template = JINJA_ENVIRONMENT.get_template('teacher/all_rosters.html')
    self.response.write(template.render(template_values))
