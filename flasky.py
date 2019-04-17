import os
from dotenv import load_dotenv
from flask_migrate import Migrate
from app import create_app, db
from app.models import User, Follow, Role, Permission, Post, Comment,\
    Club, Activity, CreateApplication, JoinApplication
from app import fake
import flask_admin
from flask_admin.contrib import sqla
from app.models import (User, Post, Comment, Club, JoinApplication,
                     CreateApplication, Activity)

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)
admin = flask_admin.Admin(name='社团管理后台', template_mode='bootstrap3')
admin.init_app(app)

admin.add_view(sqla.ModelView(User, db.session))
admin.add_view(sqla.ModelView(Post, db.session))
admin.add_view(sqla.ModelView(Comment, db.session))
admin.add_view(sqla.ModelView(Club, db.session, endpoint='club_'))
admin.add_view(sqla.ModelView(JoinApplication, db.session, category='Applications'))
admin.add_view(sqla.ModelView(CreateApplication, db.session, category='Applications'))
admin.add_view(sqla.ModelView(Activity, db.session))


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Follow=Follow, Role=Role,
                Permission=Permission, Post=Post, Comment=Comment,
                Club=Club, Activity=Activity,
                CreateApplication=CreateApplication,
                JoinApplication=JoinApplication,
                fake=fake)


@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
