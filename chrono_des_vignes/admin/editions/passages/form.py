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
from wtforms import StringField, SelectField, SubmitField, FieldList
from chrono_des_vignes.custom_validators import DataRequired, Length
from flask_babel import lazy_gettext as _

class NewKeyForm(FlaskForm):
    name: StringField = StringField(_('form.lastname'), validators=[DataRequired(), Length(max=40)])
    stands = FieldList(SelectField(_('form.stand')))  # pyright: ignore[reportUnannotatedClassAttribute]
    submit_btn: SubmitField= SubmitField('form.create')

class ChronoLoginForm(FlaskForm):
    key: StringField = StringField(_('form.key'), validators=[DataRequired()])
    submit_btn: SubmitField= SubmitField(_('form.validate'))
