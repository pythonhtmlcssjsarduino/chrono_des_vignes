'''
# Chrono Des Vignes
# a timing system for sports events
# 
# Copyright © 2024-2025 Romain Maurer
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
from wtforms.fields import TextAreaField
from chrono_des_vignes.models import User
from wtforms import StringField, PasswordField, SubmitField, EmailField, DateField
from flask_wtf.file import FileField, FileAllowed
from chrono_des_vignes.custom_validators import DataRequired, EqualTo, DbLength, Email
from chrono_des_vignes.custom_field import MultiCheckboxFieldWithDescription
from flask_babel import lazy_gettext as _
from wtforms.validators import Optional

class Login_form(FlaskForm):
    username: StringField = StringField(_('form.username'), validators=[
                           DataRequired(), DbLength(min=2, table=User, column='username')])
    password: PasswordField = PasswordField(_('form.pwd'), validators=[DataRequired()])
    submit_btn: SubmitField = SubmitField(_('form.connect'))

class Signup_form(FlaskForm):
    name: StringField = StringField(_('form.name'), validators=[DataRequired(), DbLength(table=User, column='name')])
    lastname: StringField = StringField(_('form.lastname'), validators=[DataRequired(), DbLength(table=User, column='lastname')])
    username: StringField = StringField(_('form.username'), validators=[
                           DataRequired(), DbLength(min=2, table=User, column='username')])
    email: EmailField = EmailField(_('form.email'), validators=[Optional(), Email()])
    phone: StringField = StringField(_('form.tel'))
    datenaiss: DateField = DateField(_('form.birth'), validators=[DataRequired()])
    password: PasswordField = PasswordField(_('form.pwd'), validators=[DataRequired(), DbLength(table=User, column='password')])
    repeatpassword: PasswordField = PasswordField(_('form.repetepwd'), validators=[EqualTo('password')])
    submit_btn: SubmitField = SubmitField(_('form.createaccount'))

class InscriptionConnectedForm(FlaskForm):
    parcours: MultiCheckboxFieldWithDescription = MultiCheckboxFieldWithDescription(_('form.choosedparcours'), validators=[DataRequired()])
    comment: TextAreaField = TextAreaField(_('form.comment'), [Optional()], render_kw={'style':'height:200px'})

    submit_btn: SubmitField = SubmitField(_('form.register'))

class InscriptionForm(FlaskForm):
    name: StringField = StringField(_('form.name'), validators=[DataRequired(), DbLength(table=User, column='name')])
    lastname: StringField = StringField(_('form.lastname'), validators=[DataRequired(), DbLength(table=User, column='lastname')])
    email: EmailField = EmailField(_('form.email'), validators=[Optional(), Email()])
    phone: StringField = StringField(_('form.tel'))
    datenaiss: DateField = DateField(_('form.birth'), validators=[DataRequired()])

    parcours: MultiCheckboxFieldWithDescription = MultiCheckboxFieldWithDescription(_('form.choosedparcours'), validators=[DataRequired()])
    comment: TextAreaField = TextAreaField(_('form.comment'), [Optional()], render_kw={'style':'height:200px'})

    password: PasswordField = PasswordField(_('form.pwdforconnection'), validators=[DataRequired(), DbLength(table=User, column='password')])
    repeatpassword: PasswordField = PasswordField(_('form.repetepwd'), validators=[EqualTo('password')])
    submit_btn: SubmitField = SubmitField(_('form.register'))

class ModifyForm(FlaskForm):
    name: StringField = StringField(_('form.name'), validators=[DataRequired(), DbLength(table=User, column='name')])
    lastname: StringField = StringField(_('form.lastname'), validators=[DataRequired(), DbLength(table=User, column='lastname')])
    username: StringField = StringField(_('form.username'), validators=[DataRequired(), DbLength(min=2, table=User, column='username')])
    email: EmailField = EmailField(_('form.email'), validators=[Optional(), Email()])
    phone: StringField = StringField(_('form.tel'))
    datenaiss: DateField = DateField(_('form.birth'), validators=[DataRequired()])
    profil_pic: FileField = FileField(_('form.profilpic'), validators=[FileAllowed(['jpg', 'png'])])
    submit_btn: SubmitField = SubmitField(_('form.modifyaccount'))

class ModifyPwdForm(FlaskForm):
    old_pwd: PasswordField = PasswordField(_('form.oldpwd'), validators=[DataRequired()])
    password: PasswordField = PasswordField(_('form.newpwd'), validators=[DataRequired(), DbLength(table=User, column='password')])
    repeatpassword: PasswordField = PasswordField(_('form.repetenewpwd'), validators=[EqualTo('password')])
    submit_btn: SubmitField = SubmitField(_('form.modifypassword'))
