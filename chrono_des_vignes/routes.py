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

from pathlib import Path
from flask import make_response, render_template, request, redirect, send_from_directory, abort
from chrono_des_vignes import app, LANGAGES, db, set_route
from flask_login import current_user
from chrono_des_vignes.models import Edition, Inscription, Event
from sqlalchemy import and_
from datetime import datetime
from chrono_des_vignes.admin.form import NewEventForm
from werkzeug.wrappers.response import Response

@set_route(app, '/')
def home()->str:
    # * home page of the web site
    if current_user.is_authenticated:
        user = current_user
        inscriptions = user.inscriptions.filter(Inscription.edition.has(Edition.edition_date>datetime.now())).all()
        participations = user.inscriptions.filter(Inscription.edition.has(Edition.edition_date<=datetime.now())).all()
        form = NewEventForm()
    else:
        user = None
        inscriptions = None
        participations = None
        form = None
    date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    next_events = db.session.query(Event).filter(Event.editions.any(and_(Edition.edition_date>=date,Edition.last_inscription>=date))).all()
    return render_template("0-home.html", user_data=user, inscriptions=inscriptions, events = next_events, participations=participations, form=form)

@app.route('/lang/<lang>')
def change_lang(lang:str)->Response:
    next = request.args.get('next')
    next = next.split('/')  # pyright: ignore[reportOptionalMemberAccess]
    if next[1] in LANGAGES:
        if lang==request.accept_languages.best_match(LANGAGES):
            next.pop(1)
        else:
            next[1]=lang
    else:
        if lang!=request.accept_languages.best_match(LANGAGES):
            next.insert(1, lang)
    next = '/'.join(next)
    return redirect(next)

DOC_DIR = Path(app.root_path) / 'static/doc'

@app.route('/doc/<path:path>')
@app.route('/doc/<lang>/<path:path>')
@app.route('/doc/')
def doc(path: str='', lang: str=''):
    if path == 'style.css':
        return send_from_directory(DOC_DIR, 'style.css')
    lang=lang+"/" if lang else ""
    file = Path(f'{lang}index.html' if path == '' else f'{lang}{path}index.html')
    if not (DOC_DIR/file).exists():
        return make_response(send_from_directory(DOC_DIR, '404.html'), 404)
    return send_from_directory(DOC_DIR.as_posix(), file.as_posix(), download_name=file.name)

@app.route('/doc/assets/<path:path>')
def assets_doc_files(path:str)->Response:
    return doc_file('assets', path)

@app.route('/doc/search/<path:path>')
def search_doc_files(path: str)->Response:
    return doc_file('search', path)

def doc_file(dir:str, path:str)->Response:
    return send_from_directory(DOC_DIR.as_posix(), f'{dir}/{path}', download_name=Path(path).name)
