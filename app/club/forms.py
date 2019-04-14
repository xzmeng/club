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


class ActivityForm(FlaskForm):
    name = StringField('活动名称')
    description = StringField('活动描述',
                              widget=TextArea())
    submit = SubmitField('发布活动')


class FinishActivityForm(FlaskForm):
    description = StringField('活动总结',
                              widget=TextArea())
    submit = SubmitField('结束活动')
