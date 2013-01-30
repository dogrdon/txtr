from __future__ import with_statement
from contextlib import closing
import os
import sqlite3
import datetime
import json
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response 

#database configuration
DATABASE = './db/txtr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'
#for our file input and output
LOCAL_FOLDER = './io/output'
ALLOWED_EXTENSIONS = set(['txt'])

#app
app = Flask(__name__)
app.config.from_object(__name__)
app.config['LOCAL_FOLDER'] = LOCAL_FOLDER

def hello_db():
	'''connect to the db'''
	return sqlite3.connect(app.config['DATABASE'])


def init_db():
	'''initiate our db FROM the app rather than the command line - sqlite3 /path/to/file.db < schema.sql -'''
	with closing(hello_db()) as db:
		with app.open_resource('schema.sql') as f:
			db.cursor().executescript(f.read())
		db.commit()

@app.before_request #upon this event, execute function below
def before_request():
	'''initiate db before a request FROM app'''
	g.db = hello_db()

@app.teardown_request
def teardown_request(exception):
	'''close db after a request FROM app completes'''
	g.db.close()

@app.route('/')
def show_notes():
	'''display all our notes'''
	curs = g.db.execute('SELECT id, title, text, tags FROM notes order by id desc')
	notes_get = [dict(id=row[0], title=row[1], text=row[2], tags=row[3].split(',')) for row in curs.fetchall()] 
	notes = notes_get
	'''reformat the tags in the returned notes so that they are lstripped (no leading spaces)'''
	# notes = []
	# for objs in notes_get:
	# 	nObj = {}
	# 	for item, obj in objs.iteritems():
	# 		if item != "tags":
	# 			nObj[item] = obj
	# 		else:
	# 			nObj["tags"] = [n.lstrip() for n in obj]
	# 		notes.append(nObj)


	for note in notes:
		note['tags'] = [t.strip() for t in note['tags']]
	

	return render_template('show_notes.html', notes=notes)
	
@app.route('/note/<id>')
def show_note(id):
	'''display and individual note'''
	curs = g.db.execute('SELECT id, title, text, tags, created FROM notes WHERE id = ' + id)
	note = [dict(id=row[0], title=row[1], text=row[2], tags=row[3], created=row[4]) for row in curs.fetchall()] 

	for l in note:
		#text = l['text']
		tags = l['tags']
		title = l['title'].replace(" ","_")
		text = l['text'].encode("utf-8") #probably need to do some unicode conversion
		filename = title+"-"+l['created'][0:11]
		content = 'text: ' + text + '\n' + 'tags: ' + tags

	#creating a file from a viewed note? TODO: why don't we just try basic file io here.
	#myFile = Response(note, mimetype="text/plain")
	myFile = open(LOCAL_FOLDER+'/'+filename, 'w')
	myFile.write(content)
	myFile.close()


	#TODO: AttributeError: 'Response' object has no attribute 'save'
	#myFile.save(os.path.join(app.config['LOCAL_FOLDER'], 'success'))

	return render_template('show_note.html', note=note)

@app.route('/new', methods=['POST'])
def new_note():
	'''creating a new note'''
	if not session.get('logged_in'):
		abort(401)
	g.db.execute('insert into notes (title, text, created, tags) values (?, ?, ?, ?)',
				 [request.form['title'], request.form['text'], datetime.datetime.now(), request.form['tags']])
	g.db.commit()
	flash('New note created!')
	return redirect(url_for('show_notes'))

@app.route('/note/edit/<id>')
def edit_note(id):
	'''edit our note if we'd like'''
	curs = g.db.execute('SELECT id, title, text, tags, created FROM notes WHERE id = ' + id)
	note = [dict(id=row[0], title=row[1], text=row[2], tags=row[3], created=row[4]) for row in curs.fetchall()] 
	flash('Editing Mode Activated.')
	return render_template('edit_note.html', note=note)


@app.route('/note/update/<id>', methods=['POST'])
def update_note(id):
	g.db.execute('update notes set title = ?, text = ?, tags = ? WHERE id='+id, 
		         [request.form['title'], request.form['text'], request.form['tags']])
	g.db.commit()
	flash('Note updated!')
	return redirect(url_for('show_notes'))

@app.route('/note/delete/<id>')
def delete_note(id):
	print 'deleting....'
	g.db.execute('delete FROM notes WHERE id='+id)
	g.db.commit()
	flash('Note destroyed!')
	return redirect(url_for('show_notes'))

@app.route('/tags/')
def show_tags():
	curs = g.db.execute('SELECT id, tags FROM notes')
	tags_get = json.dumps([dict(id=row[0], tags=row[1]) for row in curs.fetchall()])
	'''breaking down the tag lists to their individual tags, in primitive python'''
	data = json.loads(tags_get)

	_data = []
	tags = []
	end_tags = []

	for n in data: 
		'''function to convert tags FROM open string to a list, currently only doing most recend record.
		'''
		tags.append(n['tags'].split(','))
		_data.append({'id':n['id'], 'tags':n['tags'].split(',')})

	new_tags = json.dumps(_data)

	for each in tags:
		for end in each:
			end_tags.append(end)

	end_tags = [x.lstrip(' ') for x in end_tags] #remove leading white space
	end_tags = list(set(end_tags)) #get only unique values
	#return tags
		
		
	return render_template('tags.html', end_tags=end_tags) 

@app.route('/notes/<tag>')
def note_w_tag(tag):
	'''display only notes that are related to a specific tag'''
	print type(tag)
	tag = tag.encode('ascii','ignore')
	print type(tag)
	curs = g.db.execute('SELECT id, title, text, tags, created FROM notes WHERE tags LIKE "%' + tag + '%"')
	tag_notes = [dict(id=row[0], title=row[1], text=row[2], tags=row[3], created=row[4]) for row in curs.fetchall()] 
	
	print tag_notes
	return render_template('show_tagged_notes.html', tag_notes=tag_notes)


@app.route('/login', methods=['GET', 'POST'])
def login():
	'''login, obviously'''
	error = None
	if request.method == 'POST':
		if request.form['username'] != app.config['USERNAME']:
			error = 'Invalid username'
		elif request.form['password'] != app.config['PASSWORD']:
			error = 'Invalid password'
		else:
			session['logged_in'] = True
			flash('You are now logged in!')
			return redirect(url_for('show_notes'))
	return render_template('login.html', error=error)


@app.route('/logout')
def logout():
	session.pop('logged_in', None)
	flash('You are banished!')
	return redirect(url_for('show_notes'))



if __name__ == '__main__':
    app.run('localhost', 5001)
    
