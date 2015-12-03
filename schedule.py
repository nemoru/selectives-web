import os
import urllib
import jinja2
import webapp2
import logging
import yaml

import models
import authorizer
import logic

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Schedule(webapp2.RequestHandler):

  def RedirectToSelf(self, institution, session, student, message):
    self.redirect("/schedule?%s" % urllib.urlencode(
        {'message': message, 
         'student': student,
         'institution': institution,
         'session': session}))

  def post(self):
    # TODO: support removing a class
    auth = authorizer.Authorizer(self)
    if not auth.HasStudentAccess():
      auth.Redirect()
      return

    institution = self.request.get("institution")
    if not institution:
      logging.fatal("no institution")
    session = self.request.get("session")
    if not session:
      logging.fatal("no session")
    email = auth.student_email
    new_class_id = self.request.get("class_id")

    logic.AddStudentToClass(institution, session, email, new_class_id)
    self.RedirectToSelf(institution, session, email, "Saved Class")

  def get(self):
    auth = authorizer.Authorizer(self)
    if not auth.HasStudentAccess():
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
    email = auth.student_email

    dayparts = yaml.load(models.Dayparts.fetch(institution, session))
    if not dayparts:
      dayparts = []
    classes = models.Classes.Fetch(institution, session)
    classes = yaml.load(classes)
    try:
      _ = [c for c in classes]
    except TypeError:
      classes = []
    classes_by_daypart = {}
    dayparts_ordered = []
    
    max_row = max([daypart['row'] for daypart in dayparts])
    max_col = max([daypart['col'] for daypart in dayparts])
    
    # order the dayparts by row and col specified in yaml
    for row in range(max_row):
      dayparts_ordered.append([])
      for col in range(max_col):
        found_daypart = False
        for dp in dayparts:
          if dp['row'] == row+1 and dp['col'] == col+1:
            dayparts_ordered[row].append(dp['name'])
            found_daypart = True
        if found_daypart == False:
          dayparts_ordered[row].append('')

    eligible_classes = logic.EligibleClassIdsForStudent(
        institution, session, auth.student_entity, classes)
    for daypart in dayparts:
      classes_by_daypart[daypart['name']] = []
    classes_by_id = {}
    classes_for_catalog = []
    use_full_description = auth.CanAdministerInstitutionFromUrl()
    for c in classes:
      class_id = str(c['id'])
      if class_id not in eligible_classes:
        continue
      classes_by_id[class_id] = c
      hover_text = logic.GetHoverText(use_full_description, c)
      c['hover_text'] = hover_text
      for daypart in [s['daypart'] for s in c['schedule']]:
        classes_by_daypart[daypart].append(c)
      if not 'Core' in c['name'] and not 'Study Skills' in c['name']:
        classes_for_catalog.append(c)
    classes_for_catalog.sort(key=lambda c:c['name'])
    for c in classes_for_catalog:
      if c['description']:
        c['description'] = c['description'].replace('\n', '<br>')
    
    schedule = models.Schedule.Fetch(institution, session, email)
    schedule = schedule.split(",")

    template_values = {
      'logout_url': auth.GetLogoutUrl(self),
      'user_email' : auth.email,
      'institution' : institution,
      'session' : session,
      'message': message,
      'session_query': session_query,
      'student': auth.student_entity,
      'dayparts': dayparts,
      'classes_by_daypart': classes_by_daypart,
      'dayparts_ordered': dayparts_ordered,
      'schedule': schedule,
      'classes_by_id': classes_by_id,
      'classes_for_catalog': classes_for_catalog,
    }
    template = JINJA_ENVIRONMENT.get_template('schedule.html')
    self.response.write(template.render(template_values))
