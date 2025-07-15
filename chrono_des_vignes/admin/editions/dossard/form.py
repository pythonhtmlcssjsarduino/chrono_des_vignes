'''
# Chrono Des Vignes
# a timing system for sports events
# 
# Copyright © 2025 Romain Maurer
# This file is part of Chrono Des Vignes
# 
# Chrono Des Vignes is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
# 
# Chrono Des Vignes is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Foobar.
# If not, see <https://www.gnu.org/licenses/>.
# 
# You may contact me at chrono-des-vignes@ikmail.com
'''

from flask_wtf import FlaskForm
from wtforms import StringField, DateTimeLocalField, FloatField, SubmitField, TextAreaField, EmailField, DateField, IntegerField, TelField
from chrono_des_vignes.custom_validators import DataRequired, Length, DateTimeNotPast, DateTimeBefore, InputRequired, Email
from chrono_des_vignes.custom_field import MultiCheckboxFieldWithDescription
from flask_babel import lazy_gettext as _
from chrono_des_vignes.models import User
from wtforms.validators import Optional
from chrono_des_vignes.custom_validators import DbLength

class NewCoureurForm(FlaskForm):
    name: StringField = StringField(_('form.name'), validators=[DbLength(table=User, column='name')])
    lastname: StringField = StringField(_('form.lastname'), validators=[DbLength(table=User, column='lastname')])
    username: StringField = StringField(_('form.username'))
    email: EmailField = EmailField(_('form.email'), validators=[Optional(), Email()])
    phone: TelField = TelField(_('form.tel'))
    datenaiss: DateField = DateField(_('form.birth'), validators=[DataRequired()])

    parcours: MultiCheckboxFieldWithDescription = MultiCheckboxFieldWithDescription(_('form.choosedparcours'), validators=[DataRequired()])

    submit_btn: SubmitField = SubmitField(_('form.register'))

class ValidateNewCoureurForm(FlaskForm):
    user_id: IntegerField = IntegerField('user_id', validators=[DataRequired()])
    
    name: StringField = StringField(_('form.name'), validators=[DbLength(table=User, column='name')])
    lastname: StringField = StringField(_('form.lastname'), validators=[DbLength(table=User, column='lastname')])
    username: StringField = StringField(_('form.username'))
    email: EmailField = EmailField(_('form.email'), validators=[Optional(), Email()])
    phone: TelField = TelField(_('form.tel'))
    datenaiss: DateField = DateField(_('form.birth'), validators=[DataRequired()])

    parcours: MultiCheckboxFieldWithDescription = MultiCheckboxFieldWithDescription(_('form.choosedparcours'), validators=[DataRequired()])