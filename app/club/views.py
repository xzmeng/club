from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, make_response
from flask_login import login_required, current_user

from app.decorators import club_manager_required
from . import club
from .forms import ApplyForm, ClubCreateForm, AttendForm, ClubEditForm

from .. import db
from ..models import User, Club, Activity, ApplicationStatus, JoinApplication, \
    CreateApplication, Attend, AttendStatus


@club.route('/clubs')
def clubs():
    page = request.args.get('page', 1, type=int)
    show_all_clubs = False
    if current_user.is_authenticated:
        show_all_clubs = bool(request.cookies.get('show_all_clubs', ''))
    if show_all_clubs:
        query = Club.query
    else:
        query = current_user.clubs
    pagination = query.paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    clubs = pagination.items
    return render_template('club/clubs.html',
                           show_all_clubs=show_all_clubs,
                           clubs=clubs,
                           pagination=pagination)


@club.route('/club/<int:club_id>')
def club_detail(club_id):
    club = Club.query.get_or_404(club_id)
    management = False
    if club.chief == current_user:
        management = True
    return render_template('club/club_detail.html',
                           club=club,
                           management=management)


@club.route('/club_edit/<int:club_id>', methods=['POST', 'GET'])
@club_manager_required
def club_edit(club_id):
    club = Club.query.get_or_404(club_id)
    form = ClubEditForm(name=club.name, description=club.description)
    if form.validate_on_submit():
        name = form.name.data
        c = Club.query.filter_by(name=name).first()
        if c:
            flash('社团名：{} 已经存在！'.format(name))
            return redirect(url_for('.club_edit', club_id=club_id))
        club.name = name
        club.description = form.description.data
        db.session.add(club)
        db.session.commit()
        flash('社团信息修改成功！')
        return redirect(url_for('.club_detail', club_id=club_id))

    return render_template('club/club_edit.html',
                           form=form)


@club.route('/apply/<int:club_id>', methods=['GET', 'POST'])
@login_required
def apply(club_id):
    club = Club.query.filter_by(id=club_id).first()
    if club is None:
        flash('社团不存在！')
        return redirect(url_for('.clubs'))
    if current_user.has_joined(club):
        flash('您已经是该社团的成员！')
        return redirect(url_for('.club_detail', club_id=club_id))
    application = club.join_applications.filter_by(user_id=current_user.id,
                                                   status=ApplicationStatus.reviewing).first()
    if application:
        flash('您的申请正在审核中,请耐心等待！')
        return redirect(url_for('.club_detail', club_id=club_id))

    form = ApplyForm()
    if form.validate_on_submit():
        application = JoinApplication()
        application.description = form.description.data
        application.user = current_user
        application.club = club
        db.session.add(application)
        db.session.commit()
        flash('您的申请已经成功提交,请等待回复!')
        return redirect(url_for('.apply', club_id=club_id))

    return render_template('club/apply.html',
                           form=form, club=club)


@club.route('/join_management/<int:club_id>/<string:category>')
@login_required
@club_manager_required
def join_management(club_id, category):
    choices = ['reviewing', 'reviewed']
    if category not in choices:
        abort(404)
    if category == choices[0]:
        query = JoinApplication.query.filter_by(
            club_id=club_id,
            status=ApplicationStatus.reviewing
        )
    elif category == choices[1]:
        query = JoinApplication.query.filter_by(
            club_id=club_id
        ).filter(JoinApplication.status != ApplicationStatus.reviewing)
    page = request.args.get('page', 1, type=int)
    pagination = query.paginate(
        page, per_page=10,
        error_out=False)
    applications = pagination.items
    return render_template('club/join_management.html',
                           applications=applications,
                           category=category,
                           club_id=club_id,
                           pagination=pagination)


@club.route('/handle_application/<string:category>/<int:club_id>/<int:application_id>')
@login_required
@club_manager_required
def handle_application(category, club_id, application_id):
    choices = ['accept', 'reject']
    if category not in choices:
        abort(404)
    application = JoinApplication.query.filter_by(id=application_id).first()
    club = Club.query.filter_by(id=club_id).first()
    if category == choices[0]:
        application.status = ApplicationStatus.accepted
        application.user.clubs.append(club)
        db.session.add(application)
        db.session.commit()
        flash('新成员{}加入！'.format(application.user.name))
        return redirect(url_for('.join_management', club_id=club_id, category='reviewing'))
    elif category == choices[1]:
        application.status = ApplicationStatus.rejected
        db.session.add(application)
        db.session.commit()
        flash('{}的加入申请已经被拒绝！'.format(application.user.name))
        return redirect(url_for('.join_management', club_id=club_id, category='reviewing'))


@club.route('/apply_to_create', methods=['POST', 'GET'])
@login_required
def apply_to_create():
    form = ClubCreateForm()
    if form.validate_on_submit():
        application = CreateApplication()
        application.club_name = form.name.data
        application.description = form.description.data
        application.user = current_user
        db.session.add(application)
        db.session.commit()
        flash('您的申请已经成功提交,请等待回复!')
        return redirect(url_for('.applications', category='create'))

    return render_template('club/create_club.html',
                           form=form)


@club.route('/apply_to_attend/<int:activity_id>', methods=['POST', 'GET'])
@login_required
def apply_to_attend(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    attend = current_user.activities.filter_by(activity=activity).first()
    if attend:
        flash('您已经申请过这个活动！(状态:{})'.format(attend.get_status_text()))
        return redirect(url_for('.activity_detail', activity_id=activity.id))
    form = AttendForm()
    if form.validate_on_submit():
        attend = Attend(user=current_user, activity=activity)
        db.session.add(attend)
        db.session.commit()
        flash('您的申请已经提交成功,清等待审核!')
        return redirect(url_for('.activity_detail', activity_id=activity.id))

    return render_template('club/attend.html',
                           form=form,
                           activity=activity)


@club.route('/applications/<string:category>')
@login_required
def applications(category):
    choices = ['join', 'create']
    if category not in choices:
        abort(404)
    if category == 'join':
        applications = current_user.join_applications
    elif category == 'create':
        applications = current_user.create_applications
    return render_template('club/applications.html',
                           applications=applications,
                           category=category)


@club.route('/activities/<string:category>')
@login_required
def activities(category):
    page = request.args.get('page', 1, type=int)
    choices = ['ongoing', 'attended', 'reviewing', 'rejected', 'all']
    if category not in choices:
        abort(404)
    if category == 'ongoing':
        club_ids = [club.id for club in current_user.clubs]
        query = Activity.query.filter(Activity.club_id.in_(club_ids)).filter_by(ongoing=True)
    elif category == 'attended':
        query = Activity.query.join(Attend).filter(Attend.user == current_user). \
            filter(Activity.id == Attend.activity_id). \
            filter(Attend.status == AttendStatus.accepted)
    elif category == 'reviewing':
        query = Activity.query.join(Attend).filter(Attend.user == current_user). \
            filter(Activity.id == Attend.activity_id). \
            filter(Attend.status == AttendStatus.reviewing)
    elif category == 'rejected':
        query = Activity.query.join(Attend).filter(Attend.user == current_user). \
            filter(Activity.id == Attend.activity_id). \
            filter(Attend.status == AttendStatus.rejected)
    elif category == 'all':
        club_ids = [club.id for club in current_user.clubs]
        query = Activity.query.filter(Activity.club_id.in_(club_ids))
    pagination = query.paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False
    )
    activities = pagination.items
    return render_template('club/activities.html',
                           category=category,
                           activities=activities,
                           pagination=pagination)


@club.route('/activity/<int:activity_id>')
def activity_detail(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    attend = Attend.query.filter_by(activity_id=activity.id,
                                    user_id=current_user.id).first()
    return render_template('club/activity_detail.html',
                           activity=activity,
                           attend=attend)


@club.route('/all_clubs')
@login_required
def show_all_clubs():
    resp = make_response(redirect(url_for('.clubs')))
    resp.set_cookie('show_all_clubs', '1', max_age=30 * 24 * 60 * 60)
    return resp


@club.route('/my_clubs')
@login_required
def show_my_clubs():
    resp = make_response(redirect(url_for('.clubs')))
    resp.set_cookie('show_all_clubs', '', max_age=30 * 24 * 60 * 60)
    return resp
