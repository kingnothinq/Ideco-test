import asyncio
import pytest
import sqlite3

from datetime import datetime as dt

import nshandler as ns


@pytest.fixture
def temp_db():
    """Fixture to set up the in-memory database with test data."""

    connector = sqlite3.connect(':memory:')
    cursor = connector.cursor()
    cursor.executescript('''create table if not exists 
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
    data_set_news = [(1, 'News 1 NORMAL', 1609459200, 'News text 1 NORMAL w/ comments', False),
                     (2, 'News 2 NORMAL', 1609459200, 'News text 2 NORMAL w/o comments', False),
                     (3, 'News 3 PAST', 1577836800, 'News text 3 PAST', False),
                     (4, 'News 4 FUTURE', 1640995200, 'News text 3 FUTURE', False),
                     (5, 'News 5 DELETED', 1609459200, 'News text 4 DELETED', True)]
    data_set_cmts = [(1, 1, 'Comment 1', 1609632000, 'Comment text 1 for News 1'),
                     (2, 1, 'Comment 2', 1609459200, 'Comment text 2 for News 1'),
                     (3, 1, 'Comment 3', 1609545600, 'Comment text 3 for News 1'),
                     (4, 3, 'Comment 4', 1609459200, 'Comment text 4 for News 3'),
                     (5, 3, 'Comment 5', 1609459200, 'Comment text 4 for News 3')]
    cursor.executemany(f'INSERT OR REPLACE INTO news VALUES(?, ?, ?, ?, ?);', data_set_news)
    cursor.executemany(f'INSERT OR REPLACE INTO comments VALUES(?, ?, ?, ?, ?);', data_set_cmts)
    connector.commit()
    yield connector
    connector.close()


# Test miscellaneous
async def test_from_ts():

    ts = dt.timestamp(dt.now())
    time = dt.fromtimestamp(ts).isoformat(timespec='seconds')
    assert await ns.from_ts(ts) == time


async def test_to_ts():

    ts = dt.timestamp(dt.now().replace(microsecond=0))
    assert await ns.to_ts(dt.now().replace(microsecond=0)) == ts


# Test create_news
async def test_create_news(temp_db):

    ns.con = temp_db
    ns.cur = temp_db.cursor()
    data = {'id': 100,
            'title': 'News 100',
            'body': 'News text 100',
            'comments': [{'id': 100, 'news_id': 100, 'title': 'Comment 1', 'comment': 'Comment text 1'},
                         {'id': 101, 'news_id': 100, 'title': 'Comment 2', 'comment': 'Comment text 2'}]}
    assert await ns.create_news(data) is None


# Test delete news (change state of the DELETED flag)
async def test_change_state(temp_db):

    ns.con = temp_db
    ns.cur = temp_db.cursor()
    data = (100, 'News 100', 1609459200, 'News text 100', False)
    ns.cur.execute(f'INSERT INTO news VALUES(?, ?, ?, ?, ?);', data)
    await ns.change_state(100)
    query = ns.cur.execute(f'SELECT * FROM news WHERE news_id = 100').fetchone()[-1]
    # 0 - deleted false, 1 - deleted true
    assert query == 1


# Test get_news_one
async def test_get_news_one_t1(temp_db):

    ns.con = temp_db
    ns.cur = temp_db.cursor()
    # Sorted from the oldest to the newest: Comment 2 -> Comment 3 -> Comment 1
    expect = {'id': 1,
              'title': 'News 1 NORMAL',
              'date': '2021-01-01T05:00:00',
              'body': 'News text 1 NORMAL w/ comments',
              'deleted': 'false',
              'comments': [{'id': 2,
                            'news_id': 1,
                            'title': 'Comment 2',
                            'date': '2021-01-01T05:00:00',
                            'comment': 'Comment text 2 for News 1'},
                           {'id': 3,
                            'news_id': 1,
                            'title': 'Comment 3',
                            'date': '2021-01-02T05:00:00',
                            'comment': 'Comment text 3 for News 1'},
                           {'id': 1,
                            'news_id': 1,
                            'title': 'Comment 1',
                            'date': '2021-01-03T05:00:00',
                            'comment': 'Comment text 1 for News 1'}
                           ],
              'comments_count': 3}
    result = await ns.get_news_one(1)
    assert result == expect


async def test_get_news_one_t2(temp_db):

    ns.con = temp_db
    ns.cur = temp_db.cursor()
    expect = {'id': 2,
              'title': 'News 2 NORMAL',
              'date': '2021-01-01T05:00:00',
              'body': 'News text 2 NORMAL w/o comments',
              'deleted': 'false',
              'comments': [],
              'comments_count': 0}
    result = await ns.get_news_one(2)
    assert result == expect


async def test_get_news_one_t3(temp_db):

    ns.con = temp_db
    ns.cur = temp_db.cursor()
    expect = {'id': 3,
              'title': 'News 3 PAST',
              'date': '2020-01-01T05:00:00',
              'body': 'News text 3 PAST',
              'deleted': 'false',
              'comments': [{'id': 4,
                            'news_id': 3,
                            'title': 'Comment 4',
                            'date': '2021-01-01T05:00:00',
                            'comment': 'Comment text 4 for News 3'},
                           {'id': 5,
                            'news_id': 3,
                            'title': 'Comment 5',
                            'date': '2021-01-01T05:00:00',
                            'comment': 'Comment text 4 for News 3'}],
              'comments_count': 2}
    result = await ns.get_news_one(3)
    assert result == expect


async def test_get_news_one_t4(temp_db):

    ns.con = temp_db
    ns.cur = temp_db.cursor()
    with pytest.raises(ValueError):
        await ns.get_news_one(4)


async def test_get_news_one_t5(temp_db):

    ns.con = temp_db
    ns.cur = temp_db.cursor()
    with pytest.raises(ValueError):
        await ns.get_news_one(5)


# Test get_news_all
async def test_get_news_all(temp_db):

    ns.con = temp_db
    ns.cur = temp_db.cursor()
    # Include News 1, 2, 3 and Exclude News 4 (FUTURE), 5 (DELETED).
    # Sorted from the oldest to the newest: News 3 -> News 1 -> News 2
    expect = {'news':
                  [{'id': 3,
                    'title': 'News 3 PAST',
                    'date': '2020-01-01T05:00:00',
                    'body': 'News text 3 PAST',
                    'comments_count': 2,
                    'deleted': 'false'},
                   {'id': 1,
                    'title': 'News 1 NORMAL',
                    'date': '2021-01-01T05:00:00',
                    'body': 'News text 1 NORMAL w/ comments',
                    'deleted': 'false',
                    'comments_count': 3},
                   {'id': 2,
                    'title': 'News 2 NORMAL',
                    'date': '2021-01-01T05:00:00',
                    'body': 'News text 2 NORMAL w/o comments',
                    'deleted': 'false',
                    'comments_count': 0}],
              'news_count': 3}
    result = await ns.get_news_all()
    assert result == expect


# Create event loop
async def main():
    pass


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
