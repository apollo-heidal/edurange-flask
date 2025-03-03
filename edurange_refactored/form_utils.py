import os

from flask import flash, request, session, current_app
from flask_login import current_user

from edurange_refactored.extensions import db
from edurange_refactored.user.forms import (
    GroupForm,
    addUsersForm,
    manageInstructorForm,
    modScenarioForm,
    scenarioResponseForm,
    deleteGroupForm,
    notifyDeleteForm
)

from . import tasks
from .user.models import GroupUsers, StudentGroups, User, Responses, ScenarioGroups
from .user.models import generate_registration_code as grc
from .utils import flash_errors, responseCheck, getAttempt
from edurange_refactored.notification_utils import NotifyClear


def process_request(form):  # Input must be request.form
    dataKeys = []
    # for k in form.keys():
    #    dataKeys.append(k)
    for k in form.keys():
        if k != "csrf_token":  # csrf protection is enabled in standard application, only disabled in test app,
            dataKeys.append(k)  # so even if csrf_token is not a field in a standard request, it will still be rendered invalid

    form_switch = {
        "modScenarioForm":          ["sid", "mod_scenario"],  # "csrf_token",
        "startScenario":            ["start_scenario", "stop_scenario"],  # "csrf_token",
        "GroupForm":                ["name", "create", "size"],  # "csrf_token",
        "manageInstructorForm":     ["uName", "promote"],  # "csrf_token",
        "addUsersForm":             ["add", "groups", "uids"],  # "csrf_token",
        "scenarioResponseForm":     ["scenario", "question", "response"],  # "csrf_token",
        "deleteGroupForm":          ["group_name", "delete"],  # "csrf_token",
        "notifyDeleteForm":         ["clearButton"]  # "csrf_token"
    }

    switchVals = []
    for v in form_switch.values():
        switchVals.append(v)
    switchKeys = []
    for k in form_switch.keys():
        switchKeys.append(k)

    i = 0
    for li in switchVals:
        if li == dataKeys:
            i = switchVals.index(li)
    f = switchKeys[i]
    # print(f)

    process_switch = {
        "modScenarioForm":          process_scenarioModder,
        "startScenario":            process_scenarioStarter,
        "GroupForm":                process_groupMaker,
        "manageInstructorForm":     process_manInst,
        "addUsersForm":             process_addUser,
        "scenarioResponseForm":     process_scenarioResponse,
        "deleteGroupForm":          process_groupEraser,
        "notifyDeleteForm":         process_notifyEmpty
    }
    return process_switch[f]()


def process_scenarioModder():  # Form submitted to create a scenario |  # makeScenarioForm
    sM = modScenarioForm(request.form)  # type2Form(request.form)  #
    if sM.validate_on_submit():
        sid = sM.sid.data  # string1.data  #
        action = sM.mod_scenario.data  # string2.data  #

        return {"Start": tasks.start, "Stop": tasks.stop, "Destroy": tasks.destroy}[action].delay(sid)
    else:
        flash("Failed to start scenario")


def process_scenarioStarter():  # Form submitted to start or stop an existing scenario
    if request.form.get("start_scenario") is not None:
        os.chdir("/home/xennos/Desktop/edurange-flask/data/tmp/Foo")
        os.system("terraform apply -auto-approve")

    elif request.form.get("stop_scenario") is not None:
        os.chdir("/home/xennos/Desktop/edurange-flask/data/tmp/Foo")
        os.system("terraform destroy -auto-approve")


def process_groupMaker():  # Form to create a new group |  # GroupForm
    gM = GroupForm(request.form)  # type1Form(request.form)  #
    if gM.validate_on_submit():
        code = grc()
        name = gM.name.data
        group = StudentGroups.create(name=name, owner_id=session.get('_user_id'), code=code)
        users = []
        size = gM.size.data
        if size == 0:
            flash('Created group {0}'.format(name), 'success')
            return 'utils/create_group_response.html', group, users
        else:
            pairs = []
            gid = group.get_id()
            fName = name  # formatted group name
            name = name.replace(" ", "")  # group name with no spaces
            j = 0
            for i in range(1, size + 1):
                username = "{0}-user{1}".format(name, i)
                password = grc()
                user = User.create(
                    username=username,
                    email=username + "@edurange.org".format(i),
                    password=password,
                    active=True,
                    is_static=True
                )
                uid = user.get_id()
                GroupUsers.create(user_id=uid, group_id=gid)
                j += 1
                pairs.append((username, password))
                users.append(user)
            flash('Created group {0} and populated it with {1} temporary accounts'.format(fName, j), 'success')
            return 'utils/create_group_response.html', group, users, pairs
    else:
        flash_errors(gM)
        return 'utils/create_group_response.html',


def process_manInst():  # Form to give a specified user instructor permissions |  # manageInstructorForm
    mI = manageInstructorForm(request.form)
    if request.form.get("promote") == "true":
        if mI.validate_on_submit():
            uName = mI.uName.data  # string1.data  #
            user = User.query.filter_by(username=uName).first()
            user.update(is_instructor=True)

            flash("Made {0} an Instructor.".format(uName))
        else:
            flash_errors(mI)

    elif request.form.get("promote") == "false":
        if mI.validate_on_submit():
            uName = mI.uName.data  # string1.data  #
            user = User.query.filter_by(username=uName).first()
            user.update(is_instructor=False)

            flash("Demoted {0} from Instructor status.".format(uName))
        else:
            flash_errors(mI)


def process_addUser():  # Form to add or remove selected students from a selected group |  # addUsersForm
    uA = addUsersForm(request.form)

    if uA.validate_on_submit():
        db_ses = db.session
        group = uA.groups.data
        gid = db_ses.query(StudentGroups.id).filter(StudentGroups.name == group).first()[0]
        group = db_ses.query(StudentGroups).filter(StudentGroups.id == gid).first()
        uids = uA.uids.data  # string form
        adding = False
        if uids[-1] == ",":
            uids = uids[
                   :-1
                   ]  # slice last comma to avoid empty string after string split
        uids = uids.split(",")

        if request.form.get("add") == "true":
            adding = True

        flashStatic = ''
        for i, uid in reversed(list(enumerate(uids))):
            static = db_ses.query(User.is_static).filter(User.id == uid).first()[0]
            if not static:
                check = (
                    db_ses.query(GroupUsers)
                    .filter(GroupUsers.user_id == uid, GroupUsers.group_id == gid)
                    .first()
                )
                if check is not None:
                    if adding:
                        uids.pop(i)
                    else:
                        check.delete()
                else:
                    if adding:
                        GroupUsers.create(user_id=uid, group_id=gid)
                    else:
                        uids.pop(i)
            else:
                flashStatic = "NOTE: temporary accounts may not be added or removed from groups."
                uids.pop(i)

        if adding:
            flash("Added {0} users to group {1}. {2}".format(len(uids), group.name, flashStatic), 'success')
        else:
            flash('Removed {0} users from group {1}. {2}'.format(len(uids), group.name, flashStatic), 'success')
        users = db_ses.query(User.id, User.username, User.email, User.is_static).filter(StudentGroups.id == gid, StudentGroups.id == GroupUsers.group_id, GroupUsers.user_id == User.id)
        return 'utils/manage_student_response.html', group, users
    else:
        flash_errors(uA)
        return 'utils/manage_student_response.html',


def process_scenarioResponse():
    sR = scenarioResponseForm()
    if sR.validate_on_submit():
        sid = sR.scenario.data
        qnum = int(sR.question.data)
        resp = sR.response.data
        uid = current_user.id
        # answer checking function in utils
        score = responseCheck(qnum, sid, resp, uid)
        # get attempt number
        att = getAttempt(sid)
        Responses.create(user_id=uid, scenario_id=sid, question=qnum, student_response=resp, points=score, attempt=att)
        if score > 0:
            flash("A CORRECT answer was given for question {0}.".format(qnum))
            return 'utils/student_answer_response.html', score
        else:
            flash("An INCORRECT answer was given for question {0}.".format(qnum))
            return 'utils/student_answer_response.html', score
    else:
        flash_errors(sR)
        return False


def process_groupEraser():
    db_ses = db.session
    dG = deleteGroupForm()
    if dG.validate_on_submit():
        gname = dG.group_name.data
        grp = db_ses.query(StudentGroups).filter(StudentGroups.name == gname).first()
        grp_id = grp.id
        grp_scenarios = db_ses.query(ScenarioGroups).filter(ScenarioGroups.group_id == grp_id).first()
        grp_users = db_ses.query(GroupUsers).filter(GroupUsers.group_id == grp_id).all()
        if grp_scenarios is not None:
            flash("Cannot delete group - Are there still scenarios for this group?", "error")
        else:
            players = []
            for u in grp_users:
                players.append(db_ses.query(User).filter(User.id == u.id).first())
                u.delete()
            for p in players:
                if p is not None:
                    if p.is_static:
                        p.delete()
            grp.delete()
        flash("Successfully deleted group {0}".format(gname))
    else:
        flash_errors(dG)

def process_notifyEmpty():
    NotifyClear()

