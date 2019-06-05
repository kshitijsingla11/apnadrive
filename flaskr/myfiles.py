from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request, url_for, send_from_directory
)
import os
import io
import webbrowser
import shutil
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
from flaskr.auth import login_required
from flaskr.db import get_db
import hashlib

bp = Blueprint('myfiles', __name__)
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

@bp.route('/')
@login_required
def index():
    if g.user['username']=='admin':
         return render_template('myfiles/showtable.html')
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, description, created, author_id, extension, hash '
        ' FROM post p JOIN post_user u ON p.id = u.post_id'
        ' WHERE u.user_id = ?',
        (g.user['id'],)
    ).fetchall()
    return render_template('myfiles/index.html', posts=posts)

@bp.route('/showtable')
@login_required
def showtable():
    if g.user['username']!='admin':
        abort(403)
    return render_template('myfiles/showtable.html')

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files['file']
        error = None
        extension = file.filename.rsplit('.', 1)[1].lower()
        if not title or '.' in title:
            error = 'Title is empty or invalid.'
        if file.filename == '':
            error = 'No selected file'
        if not file or not extension in ALLOWED_EXTENSIONS:
            error = 'file extention not permited by the server'
        if error != None :
            flash(error)
        else:
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename))
            f=open(os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename),"rb")
            data=f.read()
            f.close()
            Hash=hashlib.md5(data).hexdigest()
            path=os.path.join(current_app.config['UPLOAD_FOLDER'], Hash[0])
            path=os.path.join(path, Hash[1])
            if not os.path.exists(path):
                os.makedirs(path)
            filename = Hash[2:] + "." + extension
            db = get_db()
            if db.execute('SELECT hash FROM post WHERE hash = ?', (Hash,)).fetchone() is None:
                os.rename(os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename),os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                shutil.move(os.path.join(current_app.config['UPLOAD_FOLDER'], filename),path)
            cur = db.cursor()
            cur.execute(
                'INSERT INTO post (title, description, author_id, extension,hash)'
                ' VALUES (?, ?, ?, ?,?)',
                (title, description, g.user['id'], extension,Hash)
            )
            db.commit()
            db.execute(
                'INSERT INTO post_user (post_id,user_id)'
                ' VALUES (?,?)',
                (cur.lastrowid, g.user['id'])
            )
            db.commit()
            return redirect(url_for('myfiles.index'))
    return render_template('myfiles/create.html')

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, isPublic, title, description, created, author_id, username, extension,hash'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()
    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))
    if check_author and post['author_id'] != g.user['id']:
        abort(403)
    return post

@bp.route('/getfile/<int:id>', methods=('GET', 'POST'))
@login_required
def getfile(id):
    db = get_db()
    if db.execute('SELECT * FROM post_user WHERE post_id = ? AND user_id = ?', (id,g.user['id'])).fetchone() is None:
        flash("Unauthorised Access")
        abort(403)
    post = get_post(id,False)
    Hash = post['hash']
    filename = Hash[2:] + '.' + post['extension']
    path=os.path.join(current_app.config['UPLOAD_FOLDER'], Hash[0])
    path=os.path.join(path, Hash[1])
    return send_from_directory(path, filename)

@bp.route('/publicshare/<int:id>', methods=('GET', 'POST'))
@login_required
def publicshare(id):
    post = get_post(id)
    db = get_db()
    db.execute(
        'UPDATE post SET isPublic = ?'
        ' WHERE id = ?',
        ("TRUE", id)
    )
    db.commit()
    link = current_app.config['DOMAIN_NAME'] + "publicfiles/" + str(id) 
    flash(link)
    return redirect(url_for('myfiles.index'))

@bp.route('/publicfiles/<int:id>', methods=('GET', 'POST'))
def publicfiles(id):
    post = get_post(id,False)
    if post['isPublic'] == "FALSE" :
        flash("Unauthorised Access")
        abort(403)
    Hash = post['hash']
    filename = Hash[2:] + '.' + post['extension']
    path=os.path.join(current_app.config['UPLOAD_FOLDER'], Hash[0])
    path=os.path.join(path, Hash[1])
    return send_from_directory(path, filename)

@bp.route('/privateshare/<int:id>', methods=('GET', 'POST'))
def privateshare(id):
    if request.method == 'POST':
        email=request.form['email']
        db=get_db()
        post=db.execute('SELECT id from user where email=?',(email,)).fetchone()
        print(post['id'])
        userid=post['id']
        post=get_post(id)
        db.execute(
                'INSERT INTO post_user (post_id, user_id)'
                ' VALUES (?, ?)',
                (post['id'],userid)
            )
        db.commit()
        flash("shared successfully")
        return redirect(url_for('myfiles.index'))
    return render_template('myfiles/privateshare.html')

@bp.route('/update/<int:id>', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)
    db=get_db()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        error = None
        if not title or '.' in title:
            error = 'Title is empty or invalid.'
        if error is not None:
            flash(error)
        else:
            db.execute(
                'UPDATE post SET title = ?, description = ?'
                ' WHERE id = ?',
                (title, description, id)
            )
            db.commit()
            return redirect(url_for('myfiles.index'))
    return render_template('myfiles/update.html', post=post)

@bp.route('/delete/<int:id>', methods=('POST','GET'))
@login_required
def delete(id):
    post = get_post(id)
    Hash = post['hash']
    filename = Hash[2:] + '.' + post['extension']
    path=os.path.join(current_app.config['UPLOAD_FOLDER'], Hash[0])
    path=os.path.join(path, Hash[1])
    path=os.path.join(path, filename)
    os.remove(path)
    db = get_db()
    db.execute('DELETE  FROM post_user WHERE post_id = ?', (id,))
    db.commit()
    db.execute('DELETE  FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('myfiles.index'))

@bp.route('/list')
@login_required
def list():
    if g.user['username']!='admin':
        abort(403)
    db= get_db()
    rows=db.execute('SELECT * FROM post')
    return render_template("myfiles/list.html",rows = rows)

@bp.route('/list1')
@login_required
def list1():
    if g.user['username']!='admin':
        abort(403)
    db= get_db()
    rows1=db.execute('SELECT * FROM user').fetchall()
    return render_template("myfiles/list1.html",rows1 = rows1)

@bp.route('/list2')
@login_required
def list2():
    if g.user['username']!='admin':
        abort(403)
    db= get_db()
    rows2=db.execute('SELECT * FROM post_user').fetchall()
    return render_template("myfiles/list2.html",rows2 = rows2)


# @bp.route('/<filename>/<int:id>')
# def uploaded_file(filename,id):
#     get_post(id)
#     db = get_db()
#     post=db.execute('SELECT hash,extension from post where id=?',(id,)).fetchone()
#     ext=post['extension']
#     has=post['hash']
#     path3=current_app.config['UPLOAD_FOLDER']+'/'+has[0]+'/'+has[1]+'/'+has[2:]+'.'+ext
#     DES="G:/c"
#     shutil.copy(path3,DES)
#     #f=open("filename","rb")
#     #data=f.read()
#     #f.close()
#     #Hash=md5(data).hexdigest()
#     #print(Hash)
#     #UPLOAD_FOLDER=UPLOAD_FOLDER+'/'+Hash[0]+'/'+Hash[-1]
#     #print(UPLOAD_FOLDER)
#     return render_template('myfiles/create.html')

#     #return send_from_directory(UPLOAD_FOLDER, filename)

#def share(id):
    #<a class="action" href="{{ url_for('myfiles.publicshare', id=post['id']) }}">Public Share</a>
    #<a class="action" href="{{ url_for('myfiles.privateshare', id=post['id']) }}">Private Share</a>
    #post = get_post(id)
    #filename = post['title']+'.'+post['extension']
    #link = DOMAIN_NAME + url_for('myfiles.uploaded_file',filename = filename)
    #flash("LINK : " + link)
    #return redirect(url_for('myfiles.index'))
# @bp.route('/<int:id>/publicshare')
# def publicshare(id):
#     post = get_post(id)
#     extension=post['extension']
#     Hash=post['hash']
#     path=os.path.join(current_app.config['UPLOAD_FOLDER'], Hash[0])
#     path=os.path.join(path, Hash[1])
#     s=Hash[2:]
#     link =path+url_for('myfiles.uploaded_file',filename=filename)
#     flash("LINK : " + link)
#     return redirect(url_for('myfiles.index'))

    
# @bp.route('/<int:id>/view')
# def view(id):
#     post = get_post(id)
#     db=get_db()
#     post=db.execute('SELECT hash,extension from post where id=?',(id,)).fetchone()
#     ext=post['extension']
#     has=post['hash']
#     s=has[2:]
#     path=current_app.config['UPLOAD_FOLDER']+"/"+has[0]
#     if os.path.isdir(path):
#         path1=path+"/"+has[1]
#         if os.path.isdir(path1):
#             s1=path1+'/'+s+'.'+ext
#             s=s+'.'+ext
#     #filename = post['title']+'.'+post['extension']
#     #link =path1+url_for('myfiles.uploaded_file',filename = s)
#     #return render_template('myfiles/view.html',name=s)
#     return send_from_directory(path1,s)
