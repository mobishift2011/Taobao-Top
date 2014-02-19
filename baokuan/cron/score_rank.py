#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from collections import Counter
from datetime import datetime, timedelta
from apis.base.models import Paper, Mark, Lottery

"""
* Score the paper's quiz product and sort them by their scores.
    ** data result (and will be saved in answers filed of model Paper).
    answers: {
        52834e0a7a56cb64d0981f2f: {
        5277575c7a56cb16c47e934f: 6,
        5277575c7a56cb16c47e9350: 5,
        5277575c7a56cb16c47e9351: 4,
        5277575c7a56cb16c47e9352: 3,
        5277575c7a56cb16c47e9353: 2,
        5277575c7a56cb16c47e9354: 1
    },
        52834e0a7a56cb64d0981f30: {
        5277575c7a56cb16c47e934f: 6,
        5277575c7a56cb16c47e9350: 5,
        5277575c7a56cb16c47e9351: 4,
        5277575c7a56cb16c47e9352: 3,
        5277575c7a56cb16c47e9353: 2,
        5277575c7a56cb16c47e9354: 1
    }

* Get every user's score and rank.
"""

def score_and_rank(period=None):
    if period:
        today = datetime.strptime(period, '%Y-%m-%d')
    else:
        now = datetime.now()
        today = now.replace(hour=0,minute=0,second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    score_counter = {}

    for paper in Paper.objects(period__gte=yesterday, period__lt=today):
        print u'Paper {}.{}'.format(paper.id, paper.period); print

        paper_id = str(paper.id)
        paper_answers = {}
        score_counter.setdefault(paper_id, {})

        print 'Collecting votes from user ............';
        for mark in Mark.objects(paper=paper):
            """Aggreagte and get totoal votes of a certain quiz."""
            print; print u'Voting User {}.{}'.format(mark.user, mark.user.id)

            for k, v in mark.answers.iteritems():
                quiz_id = str(k)
                product_id = str(v)
                print u'answer prod {} for quiz {}'.format(product_id, quiz_id)
                score_counter[paper_id].setdefault(quiz_id, Counter())
                score_counter[paper_id][quiz_id][product_id] += 1

        print; print 'Calculating the collection results ............'; print

        for quiz in paper.quizes:
            quiz_id = str(quiz.id)
            paper_answers.setdefault(quiz_id, {})
            quiz_size = len(quiz.products)

            if quiz_id not in score_counter[paper_id]:
                continue

            """Sort the products of a certain quiz by their voting results."""
            quiz.products = sorted(quiz.products, \
                key=lambda product: score_counter[paper_id][quiz_id][str(product.id)], reverse=True)

            """Score the products of a certain value according their rank/sort in a certain quiz."""
            for i, product in enumerate(quiz.products):
                product_id = str(product.id)
                paper_answers[quiz_id][product_id] = quiz_size - i

            print u'Products for quiz {}.{} sorted and scored: \n{}'.format(quiz.title, quiz_id, \
                [u'{}: {}'.format(str(prod.id), paper_answers[str(quiz.id)][str(prod.id)]) for prod in quiz.products])
            
            quiz.save()

        print; print 'score and rank user ............'; print
        user_score = Counter()
        user_rank = {}

        for mark in Mark.objects(paper=paper):
            user_id = str(mark.user.id)
            for quiz_id, product_id in mark.answers.iteritems():
                score = paper_answers[quiz_id][product_id]
                user_score[user_id] += score

                print u'user {}.{} get score {} for prod {} to quiz {}'.format( \
                    user_id, mark.user, score, product_id, quiz_id)
            print u"totoal score {}".format(user_score[user_id]); print

        rank_list = sorted(user_score.keys(), key=lambda x: user_score[x], reverse=True)
        if rank_list:
            min_score = user_score[rank_list[0]]
            rank = 1
            for i, uid in enumerate(rank_list):
                if user_score[uid] < min_score:
                    rank = i + 1
                    min_score = user_score[uid]

                user_rank[uid] = rank

            for mark in Mark.objects(paper=paper):
                user = mark.user
                user_id = str(user.id)
                mark.score = user_score[user_id]
                mark.rank = user_rank[user_id]
                mark.is_online = True
                mark.save()

                print u'User {}.{} score: {}, rank: {}'.format(mark.user, user_id, mark.score, mark.rank)
            print

        paper.answers = paper_answers
        paper.save()

        lottery(paper)


def lottery(paper):
    marks = Mark.objects(paper=paper, rank=1)
    Lottery.objects(paper=paper).update_one(
        set__users = [mark.user for mark in marks],
        set__score = max([mark.score for mark in marks]) if marks else 0.0,
        set__period = paper.period,
        upsert = True
    )

    bonus = 0
    lottery = Lottery.objects(paper=paper).first()
    total_awards = len(lottery.users)

    if total_awards:
        bonus = 1.0 * paper.bonus / total_awards
        bonus -= (bonus % 10)
        lottery.bonus = bonus
        lottery.save()

    print u'Lottery list for paper {} - {}'.format(paper.period, paper.id)
    print u'Total bonus: {}'.format(paper.bonus)
    print u'total awards user count: {}'.format(total_awards)
    print u'Max score {} for {}:'.format(lottery.score, lottery.period)
    for user in lottery.users:
        Mark.objects(user=user, paper=paper).update_one(
            set__total_awards = total_awards,
            set__bonus = bonus
        )

        print user.username, ' bonus:', bonus
    print


if __name__ == '__main__':
    import time, sys
    start_at = time.time()
    period = sys.argv[1] if len(sys.argv) > 1 else None
    score_and_rank(period)
    print u'Totally cost: {} s'.format(time.time()-start_at)