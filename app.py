from flask import render_template
from flask import request, redirect, url_for
from flask import Flask
import flask_login

# Own stuff
import userclass
import settings
import ldaphandler
from etherpad_cached_api import *
from _version import __version__


# Flask
app = Flask(__name__)
app.secret_key = settings.getSecretKey()


# Flask login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def user_loader(uid):
    # User does not exist
    if ldaphandler.getDn(uid) == False:
        return

    user = userclass.User()
    user.id = uid
    user.groups = ldaphandler.getGroups(user.id)
    return user


# Jinja template variables which are always the same
@app.context_processor
def templateDefaultValues():
    return dict(padwoman_version=__version__,
            title=settings.data['default']['title'])



@app.route('/login', methods=['GET', 'POST'])
def login():
    next = request.args.get('next')

    # check if user is already logged in
    if flask_login.current_user.is_authenticated:
        return redirect(next or url_for('index'))

    # Render the view
    if request.method == 'GET':
        return render_template('login.html')

    # Check if there is data to login the user
    if 'username' in request.form.keys() and 'password' in request.form.keys():
        username = request.form['username']

        # redirect to index if credentials are correct
        if ldaphandler.verifyPw(username, request.form['password']):

            user = userclass.User()
            user.id = username
            flask_login.login_user(user)

            return redirect(next or url_for('index'))

    return render_template('login.html', loginFailed=True)


# returns the human friendly name of a pad
def humanPadName(padId):
    splat = padId.split('$', 1)

    if len(splat) > 1:
        return splat[1]

    return padId


# Logout
@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for("login"))


# Serving the actual site
@app.route('/')
@flask_login.login_required
def index():
    # get selected tab
    active_group = request.args.get('group')

    # default group
    if active_group == None:
        active_group = settings.getDefaultGroup(flask_login.current_user.id,
                flask_login.current_user.getGroups())

    # Check if user is allowed to view this group
    viewableGroups = settings.getPadGroups(flask_login.current_user.id,
            flask_login.current_user.getGroups())

    groupExistsAndAllowed = active_group in viewableGroups


    # Doing all the etherpadMagic
    etherPadGroupIds = {}
    for g in viewableGroups:
        etherPadGroupIds[g] = createGroupIfNotExistsFor(g)
        # TODO: cookies setzen für user

    # Gathering information on the relevant pads for this group
    etherCurrGroup = etherPadGroupIds[active_group]

    padlist = []
    for p in listPads(etherCurrGroup):
        padlist.append({ 'title' : humanPadName(p),
            'url' : settings.data['pad']['url'] + p,
            'date' : getLastEdited(p),
            'public' : getPublicStatus(p) })

 
    return render_template('main.html', pads=padlist, groups=viewableGroups,
            active_group=active_group, 
            group_has_template=settings.groupHasTemplate(active_group),
            groupExistsAndAllowed=groupExistsAndAllowed)


# Run
if __name__ == '__main__':
     app.run(host='0.0.0.0', port='5000')
