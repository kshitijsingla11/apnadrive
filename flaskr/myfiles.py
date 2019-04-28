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
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, description, created, author_id, username, extension, hash '
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.author_id = ?',
        (g.user['id'],)
    ).fetchall()
    return render_template('myfiles/index.html', posts=posts)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files['file']
        error = None
        if not title or '.' in title:
            error = 'Title is empty or invalid.'
        if file.filename == '':
            error = 'No selected file'
        extension = file.filename.rsplit('.', 1)[1].lower()
        db = get_db()
        if file and extension in ALLOWED_EXTENSIONS:
            Hash=hashlib.md5(file.read()).hexdigest()
            # file = request.files['file']
            path=current_app.config['UPLOAD_FOLDER']+"/"+Hash[0]+"/"+Hash[1]
            if not os.path.isdir(path):
                os.mkdir(path)
                filename = Hash[2:] + '.' + extension
            filename = secure_filename(filename)
        else:
            error = 'file extention not permited by the server'
        if db.execute(
            'SELECT title FROM post WHERE title = ?', (title,)
        ).fetchone() is not None:
            error = 'Title {} is already used.'.format(title)
        if error is not None:
            flash(error)
        else:
            file.save(os.path.join(path+'/',filename))
            db.execute(
                'INSERT INTO post (title, description, author_id, extension,hash)'
                ' VALUES (?, ?, ?, ?,?)',
                (title, description, g.user['id'], extension,Hash)
            )
            db.commit()
            return redirect(url_for('myfiles.index'))
    return render_template('myfiles/create.html')

def get_post(id):
    post = get_db().execute(
        'SELECT p.id, title, description, created, author_id, username, extension,hash'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()
    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))
    if post['author_id'] != g.user['id']:
        abort(403)
    return post

@bp.route('/<int:id>/getfile', methods=('GET', 'POST'))
@login_required
def getfile(id):
    post = get_post(id)
    filename = post['title'] + '.' + post['extension']
    return uploaded_file(filename,id)

@bp.route('/<filename>')
def uploaded_file(filename,id):
    get_post(id)
    db = get_db()
    post=db.execute('SELECT hash,extension from post where id=?',(id,)).fetchone()
    ext=post['extension']
    has=post['hash']
    s=''
    for i in range(3,len(has)-2):
       s=s+has[i]
    path3=UPLOAD_FOLDER+'/'+has[1]+has[-1]+'/'+has[2]+has[-2]+'/'+s+'.'+ext
    DES="G:/c"
    shutil.copy(path3,DES)
    #f=open("filename","rb")
    #data=f.read()
    #f.close()
    #Hash=md5(data).hexdigest()
    #print(Hash)
    #UPLOAD_FOLDER=UPLOAD_FOLDER+'/'+Hash[0]+'/'+Hash[-1]
    #print(UPLOAD_FOLDER)
    return render_template('myfiles/create.html')

    #return send_from_directory(UPLOAD_FOLDER, filename)

@bp.route('/<int:id>/publicshare')
#def share(id):
    #<a class="action" href="{{ url_for('myfiles.publicshare', id=post['id']) }}">Public Share</a>
    #<a class="action" href="{{ url_for('myfiles.privateshare', id=post['id']) }}">Private Share</a>
    #post = get_post(id)
    #filename = post['title']+'.'+post['extension']
    #link = DOMAIN_NAME + url_for('myfiles.uploaded_file',filename = filename)
    #flash("LINK : " + link)
    #return redirect(url_for('myfiles.index'))
def publicshare(id):
    post = get_post(id)
    db=get_db()
    post=db.execute('SELECT hash,extension from post where id=?',(id,)).fetchone()
    ext=post['extension']
    has=post['hash']
    s=''
    path=UPLOAD_FOLDER+"/"+has[1]+has[-1]
    if os.path.isdir(path):
        path1=path+"/"+has[2]+has[-2]
        if os.path.isdir(path1):
            for i in range(3,len(has)-2):
                s=s+has[i]

            s1=path1+'/'+s+'.'+ext
            s=s+'.'+ext
    #filename = post['title']+'.'+post['extension']
    link =path1+url_for('myfiles.uploaded_file',filename = s)
    flash("LINK : " + link)
    return redirect(url_for('myfiles.index'))

@bp.route('/<int:id>/privateshare', methods=('GET', 'POST'))
def privateshare(id):
    #post = get_post(id)
    #filename = post['title']+'.'+post['extension']
    #link = DOMAIN_NAME + url_for('myfiles.uploaded_file',filename = filename)
    #flash("LINK : " + link)
    #return redirect(url_for('myfiles.index'))
    if request.method == 'POST':
        id1=request.form['description']
        db=get_db()
        post1=db.execute('SELECT id from user where username=?',(id1,)).fetchone()
        id2=post1['id']
        post=db.execute('SELECT hash,extension,title,description from post where id=?',(id,)).fetchone()
        title=post['title']
        description=post['description']
        ext=post['extension']
        has=post['hash']
        db.execute(
                'INSERT INTO post (title, description, author_id, extension,hash)'
                ' VALUES (?, ?, ?, ?,?)',
                (title, description, id2, ext,has)
            )
        db.commit()
        return redirect(url_for('myfiles.index'))
    

    return render_template('myfiles/privateshare.html')

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        error = None
        db = get_db()
        if not title:
            error = 'Title is required.'
        if db.execute(
            'SELECT title FROM post WHERE title = ? and id != ?', (title,id)
        ).fetchone() is not None:
            error = 'Title {} is already used.'.format(title)
        oldfilename = post['title'] + '.' + post['extension']
        newfilename = title + '.' + post['extension']
        newfilename = secure_filename(newfilename)
        if error is not None:
            flash(error)
        else:
            #os.rename(os.path.join(UPLOAD_FOLDER, oldfilename ),os.path.join(UPLOAD_FOLDER, newfilename ))
            db.execute(
                'UPDATE post SET title = ?, description = ?'
                ' WHERE id = ?',
                (title, description, id)
            )
            db.commit()
            return redirect(url_for('myfiles.index'))
    return render_template('myfiles/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST','GET'))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    post=db.execute('SELECT hash,extension from post where id=?',(id,)).fetchone()
    ext=post['extension']
    has=post['hash']
    s=''
    path=UPLOAD_FOLDER+"/"+has[1]+has[-1]
    if os.path.isdir(path):
        path1=path+"/"+has[2]+has[-2]
        if os.path.isdir(path1):
            for i in range(3,len(has)-2):
                s=s+has[i]
            s=path1+'/'+s+'.'+ext
            os.remove(s)
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('myfiles.index'))
    
@bp.route('/<int:id>/view')
def view(id):
    post = get_post(id)
    db=get_db()
    post=db.execute('SELECT hash,extension from post where id=?',(id,)).fetchone()
    ext=post['extension']
    has=post['hash']
    s=''
    path=UPLOAD_FOLDER+"/"+has[1]+has[-1]
    if os.path.isdir(path):
        path1=path+"/"+has[2]+has[-2]
        if os.path.isdir(path1):
            for i in range(3,len(has)-2):
                s=s+has[i]

            s1=path1+'/'+s+'.'+ext
            s=s+'.'+ext
    #filename = post['title']+'.'+post['extension']
    #link =path1+url_for('myfiles.uploaded_file',filename = s)
    #return render_template('myfiles/view.html',name=s)
    return send_from_directory(path1,s)