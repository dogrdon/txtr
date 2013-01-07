drop table if exists notes;
create table notes (
	id integer primary key autoincrement,
	title string not null,
	text string not null,
	created datetime not null, 
	tags string null	
);
