import logging

from datetime import datetime as dt
from sqlite3 import connect


async def from_ts(time):
    return dt.fromtimestamp(time).isoformat(timespec='seconds')


async def to_ts(time):
    return dt.timestamp(time)


async def drop_table(table):
    """Drop table."""

    cur.execute(f'DROP TABLE IF EXISTS {table}')
    con.commit()

    logging.debug(f'The {table} has been deleted.')


async def create_news(data):
    """Parse news from JSON and add them to the database with comments.
    Expect JSON:
    {'id': 1, 'title': 'news_1', 'body': 'The news',
    'comments': [{'id': 1, 'news_id': 1, 'title': 'comment_1', 'comment': 'Comment'}]}
    """

    event = (data['id'], data['title'], await to_ts(dt.now()), data['body'], False)
    notes = []
    for note in data['comments']:
        notes.append((note['id'], note['news_id'], note['title'], await to_ts(dt.now()), note['comment']))
    cur.execute(f'INSERT OR REPLACE INTO news VALUES(?, ?, ?, ?, ?);', event)
    cur.executemany(f'INSERT OR REPLACE INTO comments VALUES(?, ?, ?, ?, ?);', notes)
    logging.debug(f'The news has been added to the database.')
    con.commit()

    logging.info(f'The news has been created. ID is {data["id"]}.')


async def insert_data(table, data):
    """Insert data to any table."""

    cur.executemany(f'INSERT INTO {table} VALUES(Null, ?, ?, ?, ?);', data)
    con.commit()

    logging.debug(f'Information has been added to the {table} table.')


async def check_n_id(n_id):
    """Check existence of the news. If not exists, raise an exception."""

    qr_evnt = cur.execute(f'SELECT * FROM news '
                          f'WHERE news_id = {n_id} AND '
                          f'deleted = 0 AND '
                          f'date <= {await to_ts(dt.now())}').fetchone()
    if qr_evnt is None:

        logging.error(f'There is no such ID.')

        raise ValueError('There is no such ID')


async def get_news_one(n_id):
    """Request the particular news with its ID.
    Return JSON with this news, and the comments belong to it.
    {'id': 1, 'title': 'news_1', 'date': '2021-07-20T15:14:24',
    'body': 'The news', 'deleted': false,
    'comments': [{'id': 1, 'news_id': 1, 'title': 'comment_1',
                  'date': '2021-07-20T15:14:24', 'comment': 'Comment'}],
    'comments_count': 1}
    """

    async def get_cmts(notes):
        """Request all comments for the news."""

        cmts_all = []
        for note in notes:
            cmts = {'id': note[0],
                    'news_id': note[1],
                    'title': note[2],
                    'date': await from_ts(note[3]),
                    'comment': note[4]}
            cmts_all.append(cmts)

        return cmts_all


    await check_n_id(n_id)
    qr_evnt = cur.execute(f'SELECT * FROM news WHERE news_id = {n_id}').fetchone()
    qr_cmts = cur.execute(f'SELECT * FROM comments '
                          f'WHERE news_id = {qr_evnt[0]} AND '
                          f'date <= {await to_ts(dt.now())} '
                          f'ORDER BY date ASC').fetchall()

    news_one = {'id': qr_evnt[0],
                'title': qr_evnt[1],
                'date': await from_ts(qr_evnt[2]),
                'body': qr_evnt[3],
                'deleted': 'false' if qr_evnt[4] == 0 else 'true',
                'comments': await get_cmts(qr_cmts),
                'comments_count': len(qr_cmts)}

    logging.info(f'The news with ID {n_id} has been found.')

    return news_one


async def get_news_all():
    """Request all news that matches the next requirements:
    * Sorted by DATE;
    * Not deleted;
    * Not from the future.
    Return JSON with all news, and count news and comments belong to them.
    {'news': [{'id': 1, 'title': 'news_1', 'date': '2021-07-20T15:14:24',
    'body': 'The news', 'deleted': false, 'comments_count': 1}],
    'news_count': 1}
    """

    news_all = []
    for event in con.execute(f'SELECT * FROM news '
                             f'WHERE date <= {await to_ts(dt.now())} AND deleted = 0 '
                             f'ORDER BY date ASC', ):
        news_one = await get_news_one(event[0])
        news_one.pop('comments')
        news_all.append(news_one)
    news_count = len(news_all)

    if news_count:
        logging.debug(f'All the news have been found.')
    else:
        logging.debug(f'There are no stored news in the database.')

    return {'news': news_all, 'news_count': news_count}


async def change_state(n_id):
    """Change the "deleted" state to True or False.
    True - the news has been deleted.
    False - the news is actual.
    """

    await check_n_id(n_id)
    cur.execute(f'UPDATE news set deleted = 1 WHERE news_id = {n_id}')
    con.commit()

    logging.info(f'The news with ID {n_id} has been deleted.')


async def delete_news(n_id):
    """Totally delete the news and related comments."""

    await check_n_id(n_id)
    cur.execute(f'DELETE from news WHERE news_id = {n_id}')
    cur.execute(f'DELETE from comments WHERE news_id = {n_id}')
    con.commit()

    logging.info(f'The news with ID {n_id} has been completely deleted.')


# Connect to the database
con = connect('content.db')
cur = con.cursor()

# Create tables if they do not exist
cur.executescript('''create table if not exists 
                news(
                    news_id INTEGER PRIMARY KEY NOT NULL,
                    title TEXT,
                    date TIMESTAMP,
                    body TEXT,
                    deleted BOOL);
                create table if not exists 
                comments(
                    comment_id INTEGER PRIMARY KEY NOT NULL,
                    news_id INTEGER,
                    title TEXT,
                    date TIMESTAMP,
                    comment TEXT,
                    FOREIGN KEY (news_id) REFERENCES news(news_id));
                ''')
con.commit()
