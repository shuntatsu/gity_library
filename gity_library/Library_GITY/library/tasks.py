from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from your_app.models import IssuedData

def send_reminder_emails():
    # 今日の日付を取得
    today = timezone.now().date()
    # 返却日2日前の日付
    one_day_before_return_date = today + timedelta(days=2)

    # レンタル中の本を探す
    now_renting_books = IssuedData.objects.filter(return_date=None)
    for record in now_renting_books:
        # ユーザーごとに貸し出されている本を取得
        books_for_user = IssuedData.objects.filter(user=record.user, return_date=None)
        for book in books_for_user:
            # 返却予定日
            return_day = book.rental_date + timedelta(days=7 * (2 + book.extension_count))
            # 返却予定日の2日前の場合
            if return_day == one_day_before_return_date:
                send_mail_to_borrower(book, today, is_reminder=True)
            # 返却日を過ぎた場合
            elif return_day < today:
                # 返却日から2週間以内の場合は3日ごとに催促メールを送信
                if return_day + timedelta(days=14) >= today:
                    if (today - return_day).days % 3 == 0:
                        send_mail_to_borrower(book, today, is_reminder=False)
                # それ以外は遅延メールを送信
                else:
                    send_mail_to_borrower(book, today, is_reminder='OVER')

def send_mail_to_borrower(book, today, is_reminder):
    if is_reminder:
        subject = '返却のお願い: 図書館の本の返却期限が近づいています'
        message = f'{book.user.email.split("@")[0]} 様\n\n貸し出し中の本 "{book.book.book_name}" の返却期限が近づいています。お早めに返却または延長をお願いします。\n※本メールへの返信には回答できません。'
    elif is_reminder == 'OVER':
        subject = '重要: 図書館の本の返却期限が過ぎています'
        message = f'{book.user.email.split("@")[0]} 様\n\n貸し出し中の本 "{book.book.book_name}" の返却期限が大幅に過ぎています。直ちに返却してください。\n※本メールへの返信には回答できません。'
    else:
        subject = '重要: 図書館の本の返却期限が過ぎています'
        message = f'{book.user.email.split("@")[0]} 様\n\n貸し出し中の本 "{book.book.book_name}" の返却期限が過ぎています。直ちに返却してください。\n※本メールへの返信には回答できません。'
    
    send_mail(
        subject,
        message,
        'shun020415@yahoo.co.jp',
        [book.user.email],
        fail_silently=False,
    )
