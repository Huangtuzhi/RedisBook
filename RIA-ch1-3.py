#! -*- /bin/user env python
# -*- coding: utf-8 -*-

# 1.3章主要介绍了Redis的实例应用：如何实现Reddit的upvote功能。
import redis
import time

ONE_WEEK_IN_SECONDS = 7 * 86400
VOTE_SCORE = 432
ARTICLES_PER_PAGE = 5

conn = redis.StrictRedis(host='localhost', port=6379, db=0)


def post_article(conn, user, title, link):
    # 从1开始自动编号生成文章id
    article_id = str(conn.incr('article:'))

    voted = 'voted:' + article_id
    conn.sadd(voted, user)
    conn.expire(voted, ONE_WEEK_IN_SECONDS)

    now = time.time()
    article = 'article:' + article_id
    conn.hmset(article, {
        'title': title,
        'link': link,
        'poster': user,
        'time': now,
        'votes': 1,
    })

    # 注意参数顺序
    conn.zadd('score:', now + VOTE_SCORE, article)
    conn.zadd('time:', now, article)
    return article_id


def article_vote(conn, user, article):
    cutoff = time.time() - ONE_WEEK_IN_SECONDS
    # if conn.zscore('time:', article) > cutoff:
    #     return

    article_id = article.partition(':')[-1]
    if conn.sadd('voted:' + article_id, user):
        conn.zincrby('score:', article, VOTE_SCORE)
        conn.hincrby(article, 'votes', 1)


def article_downvote(conn, user, article):
    article_id = article.partition(':')[-1]
    if conn.sadd('downvoted:'+article_id, user) and int(conn.hmget(article, 'votes')[0]) > 1:
        print 'Here'
        conn.zincrby('score:', article, -VOTE_SCORE)
        conn.hincrby(article, 'votes', -1)



def get_articles(conn, page, order='score:'):
    start = (page-1) * ARTICLES_PER_PAGE
    end = start + ARTICLES_PER_PAGE - 1

    ids = conn.zrevrange(order, start, end)
    articles = []
    for id in ids:
        article_data = conn.hgetall(id)
        article_data['id'] = id  # 给hmset新增一个id项
        articles.append(article_data)
    return articles


def add_remove_groups(conn, article_id, to_add=[], to_remove=[]):
    article = 'article:' + article_id
    for group in to_add:
        conn.sadd('group:' + group, article)
    for group in to_remove:
        conn.srem('group:' + group, article)


def get_group_articles(conn, group, page, order='score:'):
    key = order + group  # key有一个新的zset
    if not conn.exists(key):
        conn.zinterstore(key,
            ['group:' + group, order],
            aggregate='max')
        conn.expire(key, 60)
    return get_articles(conn, page, key)

if __name__ == '__main__':
    post_article(conn, 'user:1000', 'the implementation of Upvote', 'http://tuzhii.com/')  # 增加文章
    # article_vote(conn, 'user:2233345886', 'article:20')  # 对某篇文章进行upvote
    # get_articles(conn, 1)  # 获取文章所有信息
    add_remove_groups(conn, '20', ['programming', 'writing'])
    add_remove_groups(conn, '21', ['programming', 'writing'])
    get_group_articles(conn, 'programming', 1, 'score:')
    article_downvote(conn, 'user:10', 'article:20') #downvote