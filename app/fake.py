import random
from random import randint
from sqlalchemy.exc import IntegrityError
from faker import Faker
from . import db
from .models import User, Role, Post, Club, Activity, Attend, JoinApplication


def users(count=20):
    fake = Faker()
    i = 0
    student = User(email='student@test.com',
                   username='student',
                   password='student',
                   confirmed=True,
                   name='王同学',
                   location='Zhengzhou',
                   about_me=fake.text(),
                   member_since=fake.past_date())
    chief = User(email='chief@test.com',
                 username='chief',
                 password='chief',
                 confirmed=True,
                 name='李同学',
                 location='Zhengzhou',
                 about_me=fake.text(),
                 member_since=fake.past_date())

    db.session.add(student)
    db.session.add(chief)
    db.session.commit()
    while i < count:
        u = User(email=fake.email(),
                 username=fake.user_name(),
                 password='password',
                 confirmed=True,
                 name=fake.name(),
                 location=fake.city(),
                 about_me=fake.text(),
                 member_since=fake.past_date())
        db.session.add(u)
        try:
            db.session.commit()
            i += 1
        except IntegrityError:
            db.session.rollback()


def posts(count=100):
    fake = Faker()
    user_count = User.query.count()
    for i in range(count):
        u = User.query.offset(randint(0, user_count - 1)).first()
        p = Post(body=fake.text(),
                 timestamp=fake.past_date(),
                 author=u)
        db.session.add(p)
    db.session.commit()


def clubs(count=100):
    fake = Faker()
    chief = User.query.filter_by(username='chief').first()
    c = Club(name='篮球社',
             description='打篮球',
             chief=chief)
    chief.clubs.append(c)
    db.session.add(chief)
    db.session.add(c)
    db.session.commit()

    for i in range(count):
        c = Club(name=fake.name(),
                 description=fake.text())
        db.session.add(c)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def apply_to_joins(count=5):
    fake = Faker()
    for u in User.query.all():
        if u.email == 'chief@test.com':
            continue
        c = Club.query.filter_by(name='篮球社').first()
        apply = JoinApplication(user=u,
                                club=c,
                                description=fake.text())
        db.session.add(apply)
        db.session.commit()


def joins(count=3):
    for u in User.query.all():
        clubs = Club.query.all()
        sample = random.sample(clubs,
                               min(len(clubs), count))
        for c in sample:
            u.clubs.append(c)
        db.session.add(u)
    db.session.commit()


def activities(count=10):
    fake = Faker()
    for c in Club.query.all():
        for i in range(count):
            activity = Activity(name=fake.name(),
                                description=fake.text(),
                                club=c,
                                ongoing=random.choice([True, False]))
            db.session.add(activity)
    db.session.commit()


def attends(count=3):
    for u in User.query.all():
        clubs = u.clubs.all()
        sample = random.sample(clubs, min(count, len(clubs)))
        for c in sample:
            activity = c.activities.first()
            attend = Attend(activity=activity, user=u)
        db.session.add(attend)
    db.session.commit()


def init():
    Role.insert_roles()
    users()
    posts()
    clubs()
    apply_to_joins()
    joins()
    activities()
    attends()
