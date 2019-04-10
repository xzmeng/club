from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField
from wtforms.widgets import TextArea


class ApplyForm(FlaskForm):
    description = StringField('申请描述',
                               widget=TextArea())
    submit = SubmitField('提交申请')


class ClubCreateForm(FlaskForm):
    name = StringField('社团名称')
    description = StringField('社团描述',
                              widget=TextArea())
    submit = SubmitField('提交申请')


class ClubEditForm(FlaskForm):
    name = StringField('社团名称')
    description = StringField('社团描述',
                              widget=TextArea())
    submit = SubmitField('提交申请')


class AttendForm(FlaskForm):
    description = StringField('申请描述',
                              widget=TextArea())
    submit = SubmitField('提交申请')


