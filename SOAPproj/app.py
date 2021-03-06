from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, RadioField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import nbi_actios as nbi

app = Flask(__name__)
pass_hash='$5$rounds=535000$B/pDI473X4BVypX.$tJcgCJANcaNqQrj8e.aKhGA3r4hQId3tYFrwGCsJoI7'
# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '$SatCom$'
app.config['MYSQL_DB'] = 'soapapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)
def turn(mode,id):
    valid = {
        'on':{'msg':'started','funct':'tetraOn','db':{'is_service':'\'YES\''}},
        'off':{'msg':'stopped','funct':'tetraOff','db':{'is_service':'\'NO\''}},
        'addRoute':{'msg':'route added','funct':'addRoute','db':{'is_route':'\'YES\''}},
        'deleteRoute':{'msg':'route deleted','funct':'deleteRoute','db':{'is_route':'\'NO\''}},
        'addBH':{'msg':'BH added','funct':'addBH','db':{'is_service':'\'YES\''}},
        'deleteBH':{'msg':'BH deleted','funct':'deleteBH','db':{'is_service':'\'NO\''}}
        }
    if mode not in valid.keys():
        raise ValueError("Status must be one of: {}".format(valid.keys()))
    # Create cursor
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM vsats WHERE t_id = %s", [id])
    vsat = cur.fetchone()
    sp=nbi.NbiFunction(vsat)
    try:
        getattr(sp,valid[mode]['funct'])()
        # Execute
        for db_cell, db_value in valid[mode]['db'].items():
            query='UPDATE vsats SET {0}={1} WHERE t_id = {2}'.format(db_cell,db_value,id)
            print (query)
            cur.execute(query)
        # Commit to DB
        mysql.connection.commit()
        #Close connection
        cur.close()
        flash_msg={'success':{'msg':'VSAT {} {}'.format(id,valid[mode]['msg']), 'type':'success'}}
        if sp.info_flash is not None:
            flash_info={'info':{'msg':sp.info_flash,'type':'info'}}
            result=dict(flash_msg, **flash_info)
        else: result=dict(flash_msg)
    except Exception as error:
        result={'error':{'msg':'CPE {} {} : {}'.format(id,valid[mode]['funct'],str(error)), 'type':'danger'}}
    for key, msg in result.items():
        flash(msg['msg'],msg['type'])
    return result


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get Form Fields
        username_candidate = request.form['username']
        password_candidate = request.form['password']

        if username_candidate =='admin':
            # Compare Passwords
            if sha256_crypt.verify(password_candidate, pass_hash):
                # Passed
                session['logged_in'] = True
                session['username'] = username_candidate
                flash('You are now logged in', 'success')
                return redirect(url_for('index'))
            else:
                error = 'Invalid login'
                return render_template('home.html', error=error)
        else:
            error = 'Username not found'
            return render_template('home.html', error=error)

    return render_template('home.html')

# About
@app.route('/about')
def about():
    return render_template('about.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('index'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('index'))

# Status
@app.route('/status', defaults={'id': None})
@app.route('/status/<string:id>')
@is_logged_in
def status(id):
    if id==None:
        # Create cursor
        cur = mysql.connection.cursor()
        # Get articles
        result = cur.execute("SELECT * FROM vsats")
        vsats = cur.fetchall()
        count_r = cur.execute("SELECT COUNT(*) FROM vsats")
        count = cur.fetchone()
        cur.close()
        return render_template('status.html', vsats=vsats, count=count)
    else:
        if id=='in':
            is_serv='YES'
        else:
            is_serv='NO'
        # Create cursor
        cur = mysql.connection.cursor()
        # Get articles
        result = cur.execute("SELECT * FROM vsats WHERE is_service=%s",[is_serv])
        vsats = cur.fetchall()
        count_r = cur.execute("SELECT COUNT(*) FROM vsats WHERE is_service=%s",[is_serv])
        count = cur.fetchone()
        cur.close()
        return render_template('status.html', vsats=vsats, count=count)

#Start VSAT
@app.route('/start/<string:id>', methods=['POST'])
@is_logged_in
def start(id):
    turn('on',id)
    return redirect(url_for('status'))

#Multiple start
@app.route('/mstart', methods=['POST'])
@is_logged_in
def mstart():
    if request.method == 'POST':
        ls=request.form.getlist('check')
        print(ls)
    return render_template('test.html',ls=ls)
#Stop VSAT
@app.route('/stop/<string:id>', methods=['POST'])
@is_logged_in
def stop(id):
    turn('off',id)
    return redirect(url_for('status'))

# BH add/delete
@app.route('/bh/<string:id>/<string:task>', methods=['POST'])
@is_logged_in
def bh(id,task):
    turn(task,id)
    return redirect(url_for('vsat',id=id))

# route add/delete
@app.route('/rt/<string:id>/<string:task>', methods=['POST'])
@is_logged_in
def rt(id,task):
    turn(task,id)
    return redirect(url_for('vsat',id=id))

#Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()
    # Get articles
    result = cur.execute("SELECT * FROM vsats")
    vsats = cur.fetchall()
    count_r = cur.execute("SELECT COUNT(*) FROM vsats")
    count = cur.fetchone()

    if result > 0:
        return render_template('dashboard.html', vsats=vsats, count=count)
    else:
        msg = 'No VSATs found'
        return render_template('dashboard.html', msg=msg, count={'COUNT(*)':0})
    # Close connection
    cur.close()
    return render_template('dashboard.html')

# Add VSAT Form Class
class AddvsatForm(Form):
    t_id = StringField('Terminal ID', [validators.Length(min=1, max=20)])
    t_name = StringField('TerminalName', [validators.Length(min=4, max=25)])
    bh_vlan = StringField('BH VLAN', [validators.Length(min=1, max=25)])
    bh_name = StringField('BH profile name', [validators.Length(min=2, max=25)])
    bh_src = RadioField('Backhauling Source', choices=[('PROFILE','PROFILE'),('VR','VR')], default='PROFILE')
    bh_src_ip = StringField('BH source IP', [validators.Length(min=7, max=25)], default="0.0.0.0")
    is_route = RadioField('IP Route', choices=[('YES','YES'),('NO','NO')], default='YES')
    t_rt_ip = StringField('Route address', [validators.Length(min=7, max=25)])
    t_rt_msk = StringField('Route mask', [validators.Length(min=7, max=25)])
    t_rt_gw = StringField('Route gateway', [validators.Length(min=7, max=25)])
    is_service = RadioField('In service now', choices=[('YES','YES'),('NO','NO')], default='YES')
# User Register
@app.route('/add_vsat', methods=['GET', 'POST'])
def add_vsat():
    form = AddvsatForm(request.form)
    if request.method == 'POST':
        if form.validate():
            t_id = form.t_id.data
            t_name = form.t_name.data
            bh_vlan = form.bh_vlan.data
            bh_name = form.bh_name.data
            bh_src = form.bh_src.data
            bh_src_ip = form.bh_src_ip.data
            is_route = form.is_route.data
            t_rt_ip = form.t_rt_ip.data
            t_rt_msk = form.t_rt_msk.data
            t_rt_gw = form.t_rt_gw.data
            is_service = form.is_service.data
            # Create cursor
            cur = mysql.connection.cursor()
            # Execute query
            if not cur.execute("SELECT t_id FROM vsats WHERE t_id = %s", [t_id]):
                cur.execute("INSERT INTO vsats(t_id, t_name, bh_vlan, bh_name, bh_src, bh_src_ip, is_route, t_rt_ip, t_rt_msk, t_rt_gw, is_service) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (t_id, t_name, bh_vlan, bh_name, bh_src, bh_src_ip, is_route, t_rt_ip, t_rt_msk, t_rt_gw, is_service))
                # Commit to DB
                mysql.connection.commit()
                # Close connection
                cur.close()
                flash('VSAT '+t_id+' added successfuly', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Terminal ID already exists', 'danger')
                return render_template('addvsat.html', form=form)
        else:
            flash('Validation wrong', 'danger')
            return render_template('addvsat.html', form=form)
    return render_template('addvsat.html', form=form)

#Delete VSAT
@app.route('/delete_vsat/<string:id>', methods=['POST'])
@is_logged_in
def delete_vsat(id):
    # Create cursor
    cur = mysql.connection.cursor()
    # Execute
    cur.execute("DELETE FROM vsats WHERE t_id = %s", [id])
    # Commit to DB
    mysql.connection.commit()
    #Close connection
    cur.close()
    flash('VSAT '+id+' Deleted', 'success')
    return redirect(url_for('dashboard'))

# Edit VSAT
@app.route('/edit_vsat/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_vsat(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM vsats WHERE t_id = %s", [id])
    vsat = cur.fetchone()
    cur.close()
    # Get form
    form = AddvsatForm(request.form)
    # Populate article form fields
    form.t_id.data=str(vsat['t_id'])
    form.t_name.data=str(vsat['t_name'])
    form.bh_vlan.data=str(vsat['bh_vlan'])
    form.bh_name.data=str(vsat['bh_name'])
    form.bh_src.data=str(vsat['bh_src'])
    form.bh_src_ip.data=str(vsat['bh_src_ip'])
    form.is_route.data = str(vsat['is_route'])
    form.t_rt_ip.data=str(vsat['t_rt_ip'])
    form.t_rt_msk.data=str(vsat['t_rt_msk'])
    form.t_rt_gw.data=str(vsat['t_rt_gw'])
    form.is_service.data=str(vsat['is_service'])

    if request.method == 'POST' and form.validate():
        t_name=request.form['t_name']
        bh_name=request.form['bh_name']
        bh_vlan=request.form['bh_vlan']
        bh_src=request.form['bh_src']
        bh_src_ip=request.form['bh_src_ip']
        is_route=request.form['is_route']
        t_rt_ip=request.form['t_rt_ip']
        t_rt_msk=request.form['t_rt_msk']
        t_rt_gw=request.form['t_rt_gw']
        is_service=request.form['is_service']
        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(t_name)
        # Execute
        cur.execute ("UPDATE vsats SET t_name=%s, bh_vlan=%s, bh_name=%s, bh_src=%s, bh_src_ip=%s, is_route=%s, t_rt_ip=%s, t_rt_msk=%s, t_rt_gw=%s, is_service=%s WHERE t_id=%s",(t_name, bh_vlan, bh_name, bh_src, bh_src_ip, is_route, t_rt_ip, t_rt_msk, t_rt_gw, is_service, id))
        # Commit to DB
        mysql.connection.commit()
        #Close connection
        cur.close()
        flash('VSAT {} Updated'.format(id), 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_vsat.html', form=form, id=id)

#Single VSAT
@app.route('/vsat/<string:id>/')
def vsat(id):
    # Create cursor
    cur = mysql.connection.cursor()
    # Get article
    result = cur.execute("SELECT * FROM vsats WHERE t_id = %s", [id])

    vsat = cur.fetchone()

    return render_template('vsat.html', vsat=vsat)

@app.route('/test', defaults={'id': None})
@app.route('/test/<string:id>')
@is_logged_in
def status_s(id):
    if id==None:
        # Create cursor
        cur = mysql.connection.cursor()
        # Get articles
        result = cur.execute("SELECT * FROM vsats")
        vsats = cur.fetchall()
        count_r = cur.execute("SELECT COUNT(*) FROM vsats")
        count = cur.fetchone()
        cur.close()
        return render_template('status0.html', vsats=vsats, count=count)
    else:
        if id=='in':
            is_serv='YES'
        else:
            is_serv='NO'
        # Create cursor
        cur = mysql.connection.cursor()
        # Get articles
        result = cur.execute("SELECT * FROM vsats WHERE is_service=%s",[is_serv])
        vsats = cur.fetchall()
        count_r = cur.execute("SELECT COUNT(*) FROM vsats WHERE is_service=%s",[is_serv])
        count = cur.fetchone()
        cur.close()
        return render_template('status0.html', vsats=vsats, count=count)

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(host='127.0.0.1', port=5011, debug=True)
