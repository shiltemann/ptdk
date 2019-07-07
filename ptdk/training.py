import functools
import yaml
import shutil

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from planemo import cli
from planemo.training import Training
from ptdk.db import get_db
from werkzeug.security import check_password_hash, generate_password_hash
from zipfile import ZipFile 


tuto = Blueprint('training', __name__)

with open("config.yaml", "r") as stream:
    config = yaml.load(stream, Loader=yaml.FullLoader)


@tuto.route('/', methods=('GET','POST'))
def index():
    '''Get tutorial attributes'''
    if request.method == 'POST':
        tuto = {
            'name': request.form['name'],
            'title': request.form['title'],
            'galaxy_url': request.form['galaxy_url'],
            'workflow_id': request.form['workflow_id'],
            'zenodo': request.form['zenodo']
        }
        db = get_db()
        error = None

        if not tuto['galaxy_url']:
            error = 'Galaxy URL is required.'
        elif not tuto['workflow_id']:
            error = 'Workflow id is required.'
        elif not tuto['name']:
            error = 'Name for tutorial is required.'
        elif tuto['galaxy_url'] not in config:
            error = 'No API key for this Galaxy instance.'
        
        tuto['api_key'] = config[tuto['galaxy_url']]['api_key']
            
        if error is None:
            tuto['status'] = 'in creation'

            db.execute(
                'INSERT INTO tutorials (name, title, galaxy_url, workflow_id, zenodo, status) VALUES (?, ?, ?, ?, ?, ?)',
                (tuto['name'], tuto['title'], tuto['galaxy_url'], tuto['workflow_id'], tuto['zenodo'], tuto['status'])
            )
            db.commit()
            zip_fp = generate(tuto)
            return render_template('training/index.html', zip_fp=zip_fp)

        flash(error)

    return render_template('training/index.html')


def generate(tuto):
    '''Generate skeleton of a tutorial'''
    shutil.rmtree('topics', ignore_errors=True)
    shutil.rmtree('metadata', ignore_errors=True)

    kwds = {
        'topic_name': 'topic',
        'topic_title': "New topic",
        'topic_target': "use",
        'topic_summary': "Topic summary",
        'tutorial_name': tuto['name'],
        'tutorial_title': tuto['title'],
        'hands_on': True,
        'slides': False,
        'workflow_id': tuto['workflow_id'],
        'zenodo_link': tuto['zenodo'],
        'galaxy_url': tuto['galaxy_url'],
        'galaxy_api_key': tuto['api_key'],
        'workflow': None,
        'datatypes': None
    }
    train = Training(kwds)

    ctx = cli.Context()
    ctx.planemo_directory = "/tmp/planemo-test-workspace"
    train.init_training(ctx)

    zip_fp = "/static/%s" % (tuto['name'])
    dir_path = "topics/topic/tutorials/%s" % (tuto['name'])
    shutil.make_archive("ptdk/%s" % zip_fp, 'zip', dir_path)

    shutil.rmtree('topics', ignore_errors=True)
    shutil.rmtree('metadata', ignore_errors=True)

    return "%s.zip" % zip_fp

