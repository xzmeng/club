from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, make_response
from flask_login import login_required, current_user
from sqlalchemy import or_, and_

from app.decorators import club_manager_required
from . import club
from .forms import ApplyForm, ClubCreateForm, AttendForm, ClubEditForm, ActivityForm, FinishActivityForm

from .. import db
from ..models import User, Club, Activity, ApplicationStatus, JoinApplication, \
    CreateApplication, Attend, AttendStatus, ActivityStatus, Post


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


@club.route('/club/<int:club_id>/<string:category>')
def club_detail(club_id, category):
    choices = ['ongoing', 'finished', 'reviewing', 'rejected']
    if category not in choices:
        abort(404)

    club = Club.query.get_or_404(club_id)
    management = False
    if club.chief == current_user:
        management = True
        if category == 'reviewing':
            activities = Activity.query.filter_by(club_id=club_id). \
                filter_by(status=ActivityStatus.reviewing)
        elif category == 'rejected':
            activities = Activity.query.filter_by(club_id=club_id). \
                filter_by(status=ActivityStatus.rejected)
    if category == 'ongoing':
        activities = Activity.query.filter_by(club_id=club_id). \
            filter(or_(Activity.status == ActivityStatus.accepted, ActivityStatus == ActivityStatus.rollcall))
    elif category == 'finished':
        activities = Activity.query.filter_by(club_id=club_id). \
            filter_by(status=ActivityStatus.finished)
    page = request.args.get('page', 1, type=int)
    query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('club/club_detail.html',
                           club=club,
                           management=management,
                           activities=activities,
                           category=category,
                           posts=posts,
                           pagination=pagination,
                           )


@club.route('/club_edit/<int:club_id>', methods=['POST', 'GET'])
@club_manager_required
def club_edit(club_id):
    club = Club.query.get_or_404(club_id)
    form = ClubEditForm(name=club.name, description=club.description)
    if form.validate_on_submit():
        name = form.name.data
        c = Club.query.filter_by(name=name).first()
        if c != club and c:
            flash('社团名：{} 已经存在！'.format(name))
            return redirect(url_for('.club_edit', club_id=club_id,
                                    category='ongoing'))
        club.name = name
        club.description = form.description.data
        db.session.add(club)
        db.session.commit()
        flash('社团信息修改成功！')
        return redirect(url_for('.club_detail', club_id=club_id,
                                category='ongoing'))

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
        return redirect(url_for('.club_detail', club_id=club_id, category='ongoing'))
    application = club.join_applications.filter_by(user_id=current_user.id,
                                                   status=ApplicationStatus.reviewing).first()
    if application:
        flash('您的申请正在审核中,请耐心等待！')
        return redirect(url_for('.club_detail', club_id=club_id, category='ongoing'))

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
        if CreateApplication.query.filter_by(club_name=form.name.data):
            flash('已经有该名字的申请！')
            return redirect(url_for('.apply_to_create'))
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
        query = Activity.query.filter(Activity.club_id.in_(club_ids)). \
            filter_by(status=ActivityStatus.accepted)
    elif category == 'attended':
        query = Activity.query.join(Attend).filter(Attend.user == current_user). \
            filter(Activity.id == Attend.activity_id). \
            filter(Activity.status != ActivityStatus.rejected). \
            filter(Attend.status == AttendStatus.accepted)
    elif category == 'reviewing':
        query = Activity.query.join(Attend).filter(Attend.user == current_user). \
            filter(Activity.id == Attend.activity_id). \
            filter(Activity.status == ActivityStatus.accepted). \
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
    rollcall = None
    if activity.status == ActivityStatus.rollcall:
        if attend:
            if attend.status == AttendStatus.attended:
                rollcall = 'attended'
            else:
                rollcall = 'notattended'
    status_dict = {
        ActivityStatus.reviewing: 'reviewing',
        ActivityStatus.accepted: 'ongoing',
        ActivityStatus.rejected: 'rejected',
        ActivityStatus.finished: 'finished',
        ActivityStatus.rollcall: 'rollcalling'
    }
    status = status_dict[activity.status]

    management = False
    if current_user == activity.club.chief:
        management = True
    return render_template('club/activity_detail.html',
                           activity=activity,
                           attend=attend,
                           status=status,
                           management=management,
                           rollcall=rollcall)


@club.route('/activity_management/<int:activity_id>/<string:category>')
def activity_management(activity_id, category):
    activity = Activity.query.get_or_404(activity_id)
    if category == 'reviewing':
        attends = Attend.query.filter_by(activity=activity). \
            filter_by(status=AttendStatus.reviewing)
    elif category == 'reviewed':
        attends = Attend.query.filter_by(activity=activity). \
            filter(Attend.status != AttendStatus.reviewing)
    elif category == 'attended':
        attends = Attend.query.filter_by(activity=activity). \
            filter(Attend.status == AttendStatus.attended)
    elif category == 'notattended':
        attends = Attend.query.filter_by(activity=activity). \
            filter(Attend.status == AttendStatus.accepted)
    rollcall = activity.status == ActivityStatus.rollcall
    return render_template('club/activity_management.html',
                           activity=activity,
                           attends=attends,
                           category=category,
                           rollcall=rollcall
                           )


@club.route('/activity_management_admin/<string:category>')
def activity_management_admin(category):
    if category == 'reviewing':
        activities = Activity.query.filter_by(status=ActivityStatus.reviewing)
    elif category == 'reviewed':
        activities = Activity.query.filter(Activity.status != ActivityStatus.reviewing)

    page = request.args.get('page', 1, type=int)
    pagination = activities.paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False
    )
    activities = pagination.items
    return render_template('club/activity_management_admin.html',
                           activities=activities,
                           category=category,
                           pagination=pagination
                           )


@club.route('/finish_activity/<int:activity_id>', methods=['POST', 'GET'])
def finish_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if current_user != activity.club.chief:
        abort(403)
    if activity.status != ActivityStatus.accepted:
        flash('活动不再进行中！')
        return redirect(url_for('.activity_detail', activity_id=activity_id))
    form = FinishActivityForm()
    if form.validate_on_submit():
        activity.status = ActivityStatus.finished
        activity.conclusion = form.description.data
        db.session.add(activity)
        db.session.commit()
        flash('活动成功结束！')
        return redirect(url_for('.activity_detail', activity_id=activity_id))
    return render_template('club/finish.html',
                           form=form)


@club.route('/start_rollcall/<int:activity_id>')
def start_rollcall(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if activity.status != ActivityStatus.accepted:
        flash('活动不在进行中或者点名已经开始！')
        return redirect(url_for('.activity_management',
                                activity_id=activity_id,
                                category='attended'))
    activity.status = ActivityStatus.rollcall
    db.session.add(activity)
    db.session.commit()
    flash('点名开始！')
    return redirect(url_for('.activity_management',
                            activity_id=activity_id,
                            category='attended'))


@club.route('/rollcall/<int:activity_id>')
def rollcall(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if activity.status != ActivityStatus.rollcall:
        flash('活动没有在点名阶段！')
        return redirect(url_for('.activity_detail',
                                activity_id=activity_id))
    attend = Attend.query.filter_by(activity=activity, user=current_user).first()
    if not attend:
        flash('你没有参加该活动或者审核没有通过！')
        return redirect(url_for('.activity_detail',
                                activity_id=activity_id))
    if attend.status == AttendStatus.attended:
        flash('你已经答到过了！')
        return redirect(url_for('.activity_detail',
                                activity_id=activity_id))
    attend.status = AttendStatus.attended
    db.session.add(attend)
    db.session.commit()
    flash('成功答到！')
    return redirect(url_for('.activity_detail',
                            activity_id=activity_id))


@club.route('/<int:activity_id>/roll_call', methods=['POST', 'GET'])
@login_required
def rollcall_chief(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if current_user != activity.club.chief:
        abort(403)

    attends = Attend.query.filter(
        or_(Attend.status == AttendStatus.accepted,
            Attend.status == AttendStatus.attended)
    )
    if request.method == 'POST':
        print('post')
        for attend in attends:
            if request.form.get(str(attend.id)):
                attend.status = AttendStatus.attended
            else:
                attend.status = AttendStatus.accepted
            db.session.add(attend)
        db.session.commit()
        flash('点名结果已经保存！')
        return redirect(url_for('.rollcall_chief',
                                activity_id=activity_id))

    return render_template('club/rollcall_chief.html',
                           attends=attends,
                           AttendStatus=AttendStatus,
                           activity=activity)


@club.route('/club_create_admin/<string:category>')
@login_required
def club_create_admin(category):
    if category == 'reviewing':
        applications = CreateApplication.query.filter_by(status=ApplicationStatus.reviewing)
    elif category == 'reviewed':
        applications = CreateApplication.query.filter(CreateApplication.status != ApplicationStatus.reviewing)

    page = request.args.get('page', 1, type=int)
    pagination = applications.paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False
    )
    applications = pagination.items
    return render_template('club/application_management_admin.html',
                           applications=applications,
                           category=category,
                           pagination=pagination
                           )


@club.route('/club_handle/<int:app_id>/<string:category>')
def handle_club(app_id, category):
    app = CreateApplication.query.get_or_404(app_id)
    # if current_user != activity.activity.club.chief:
    #     abort(403)
    if category == 'accept':
        app.status = ApplicationStatus.accepted
        club = Club()
        club.name = app.club_name
        club.description = app.description
        club.chief = app.user
        club.members.append(app.user)
        db.session.add(app)
        db.session.add(club)
        db.session.commit()
        flash('操作成功!')
        return redirect(url_for('.club_create_admin',
                                category='reviewing'))
    elif category == 'reject':
        app.status = ApplicationStatus.rejected
        db.session.add(app)
        db.session.commit()
        flash('操作成功!')
        return redirect(url_for('.club_create_admin',
                                category='reviewing'))
    abort(404)


@club.route('/activity_handle/<int:activity_id>/<string:category>')
def handle_activity(activity_id, category):
    activity = Activity.query.get_or_404(activity_id)
    # if current_user != activity.activity.club.chief:
    #     abort(403)
    if category == 'accept':
        activity.status = ActivityStatus.accepted
        db.session.add(activity)
        db.session.commit()
        flash('操作成功!')
        return redirect(url_for('.activity_management_admin',
                                category='reviewing'))
    elif category == 'reject':
        activity.status = ActivityStatus.rejected
        db.session.add(activity)
        db.session.commit()
        flash('操作成功!')
        return redirect(url_for('.activity_management_admin',
                                category='reviewing'))
    abort(404)


@club.route('/activity_publish/<int:club_id>', methods=['GET', 'POST'])
def activity_publish(club_id):
    club = Club.query.get_or_404(club_id)
    if club.chief != current_user:
        abort(403)
    form = ActivityForm()
    if form.validate_on_submit():
        activity = Activity()
        activity.name = form.name.data
        activity.description = form.description.data
        activity.club = club
        db.session.add(activity)
        db.session.commit()
        flash('您的活动已经成功发布,请等待联合会审核！')
        return redirect(url_for('.activity_detail', activity_id=activity.id))
    return render_template('club/activity_publish.html',
                           form=form)


@club.route('/handle_attend/<int:attend_id>/<string:category>')
def handle_attend(attend_id, category):
    attend = Attend.query.get_or_404(attend_id)
    if current_user != attend.activity.club.chief:
        abort(403)
    if category == 'accept':
        attend.status = AttendStatus.accepted
        db.session.add(attend)
        db.session.commit()
        flash('操作成功!')
        return redirect(url_for('.activity_management',
                                activity_id=attend.activity_id,
                                category='reviewing'))
    elif category == 'reject':
        attend.status = AttendStatus.rejected
        db.session.add(attend)
        db.session.commit()
        flash('操作成功!')
        return redirect(url_for('.activity_management',
                                activity_id=attend.activity_id,
                                category='reviewing'))
    abort(404)


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


@club.route('/about')
def about():
    return render_template('club/about.html')


@club.route('/admin')
def admin():
    if not current_user.is_chairman:
        flash('只有主席才能访问！')
        abort(403)
    return render_template('club/admin.html')


@club.route('/statistics/student')
@login_required
def student_info():
    info = {}
    for club in current_user.clubs:
        activity_ids = [activity.id for activity in club.activities]
        info[club.name] = Attend.query. \
            filter(Attend.user == current_user, Attend.activity_id.in_(activity_ids)).count()
    bar_labels = info.keys()
    bar_values = info.values()
    return render_template('club/student_info.html',
                           title='学生统计', max=10,
                           labels=bar_labels,
                           values=bar_values,
                           info=info)


@club.route('/statistics/club/<int:club_id>/<string:category>')
@login_required
def club_info(club_id, category):
    club = Club.query.get_or_404(club_id)
    activity_ids = [activity.id for activity in club.activities]
    info = {}
    if category == 'members':
        title = '成员统计'
        for member in club.members:
            info[member.name] = Attend.query.filter(
                and_(Attend.activity_id.in_(activity_ids),
                     Attend.user == member)).count()
    elif category == 'activities':
        title = '活动统计'
        for activity in club.activities:
            info[activity.name] = Attend.query.filter(
                Attend.activity == activity
            ).count()

    bar_labels = info.keys()
    bar_values = info.values()
    return render_template('club/club_info.html',
                           title=title, max=10,
                           labels=bar_labels,
                           values=bar_values,
                           info=info,
                           club=club)

@club.route('/statistics/admin')
@login_required
def admin_info():
    info = {}
    for club in Club.query.all():
        activity_ids = [activity.id for activity in club.activities]
        info[club.name] = Attend.query.filter(Attend.activity_id.in_(activity_ids)).count()

    title = '社团活跃度'
    bar_labels = info.keys()
    bar_values = info.values()
    return render_template('club/admin_info.html',
                           title=title, max=max(bar_values),
                           labels=bar_labels,
                           values=bar_values,
                           info=info)
