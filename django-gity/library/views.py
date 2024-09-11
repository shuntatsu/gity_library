from datetime import timedelta
import io
import json
import requests
import xml.etree.ElementTree as ET

from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.contrib import messages, auth
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, FileResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView

from authlib.integrations.django_client import OAuth

from .forms import BookForm, SearchBookForm, SearchUserForm, WantBookForm
from .models import Book, IssuedData, QRCode, Want_Book
from .makeUserQr import make_qr
from .decorator import is_superuser, rate_limit
from .qr import generate_qr_code_pdf

# keyclock
OAUTH = OAuth()
OAUTH.register(
    name='rp',
    client_id=settings.OIDC_CLIENT_ID,
    client_secret=settings.OIDC_CLIENT_SECRET,
    access_token_url=settings.TOKEN_ENDPOINT,
    authorize_url=settings.AUTHORIZATION_ENDPOINT,
    jwks_uri=settings.JWKS_URI,
    client_kwargs={
        'scope': 'openid',
        'code_challenge_method': 'S256',
        'response_type': 'code',
    },
)

# ログイン一次処理用
"""
関数: login_op
    OPへのログインを処理するAPI
引数:
    request: DjangoのHttpRequestオブジェクト
戻り値:
    認証リダイレクトのレスポンス
"""
def login_op(request):
    # Djangoのセッションから'session_key'を削除します
    if 'session_key' in request.session:
        del request.session['session_key']
        # セッションキーを削除したことをデバッグ用に出力
        # print('Session key removed')

    # リダイレクトURIを構築します
    redirect_uri = request.build_absolute_uri(
        reverse_lazy('login_rp')
    )
    # リダイレクトURIをデバッグ用に出力
    # print(f'Redirect URI: {redirect_uri}')

    # トークンレスポンスが発生したときにURLが失われないように、次のURLを保持します
    if 'next' in request.GET:
        request.session['url_next_to_login'] = request.GET['next']
        # 次のURLをセッションに保存したことをデバッグ用に出力
        # print(f"Next URL saved in session: {request.GET['next']}")

    # 認証リクエストを行い、リダイレクトレスポンスを返します
    return OAUTH.rp.authorize_redirect(request, redirect_uri)

# ログイン二次処理用
"""
関数: login_rp
    RPとセッションを作成するためのリダイレクトエンドポイント
引数:
    request: DjangoのHttpRequestオブジェクト
戻り値:
    ユーザーを適切なURLにリダイレクトするレスポンス、またはエラーメッセージ
"""
def login_rp(request):
    # エラーがGETパラメータに含まれている場合、エラーメッセージを表示
    if 'error' in request.GET:
        err_msg = request.GET.get('error_description', 'An error occurred')
        # エラーメッセージを返す
        return HttpResponse(err_msg)
    
    # デバッグ用の出力
    # print(OAUTH.rp)
    # print(request)
    
    # ユーザーを認証
    user = auth.authenticate(request, client=OAUTH.rp)
    
    # ユーザーが認証されている場合
    if user is not None and user.is_authenticated:
        # ユーザーをログイン
        auth.login(request, user)

        # リダイレクトURLを取得し、セッションから削除
        redirect_url = request.session.get('url_next_to_login', settings.LOGIN_REDIRECT_URL)
        if 'url_next_to_login' in request.session:
            del request.session['url_next_to_login']

        # デバッグ用の出力
        # print(redirect_url)

        # ユーザーをリダイレクト
        return redirect(redirect_url)
    
    # デバッグ用の出力
    # print(user)

    # エラーメッセージを返す（テストコード）
    return HttpResponse('error')

"""
関数: logout
    ユーザーをログアウトし、Keycloakのログアウトエンドポイントにリダイレクトします
引数:
    request: DjangoのHttpRequestオブジェクト
戻り値:
    Keycloakのログアウトエンドポイントへのリダイレクトレスポンス
"""
def logout(request):
    # Djangoのログアウト関数を呼び出してユーザーをログアウト
    auth_logout(request)
    
    # KeycloakのログアウトエンドポイントURL
    keycloak_logout_url = 'https://sso.gity.co.jp/realms/gity/protocol/openid-connect/logout'
    
    # Keycloakのログアウトエンドポイントにリダイレクト
    return redirect(keycloak_logout_url)

"""
関数: home
    ユーザーのホームページを表示し、図書の延長やQRコードの更新を処理します。
引数:
    request: HTTPリクエストオブジェクト
戻り値:
    レンダリングされたホームページのHTTPレスポンス
"""
@csrf_exempt
@login_required(login_url='/login')
def home(request):
    # セッションの有効期限を取得（単位は秒）
    session_age = settings.SESSION_COOKIE_AGE if hasattr(settings, 'SESSION_COOKIE_AGE') else 15 * 60

    # ユーザーIDを取得
    user_id = request.user.id if request.user.is_authenticated else None

    if request.method == 'POST':
        if 'extend_button' in request.POST:
            # 延長ボタンが押された場合の処理
            book_id = request.POST.get('extend_button')
            issued_data = IssuedData.objects.filter(book__bar_code=book_id, user=request.user, return_date__isnull=True).first()
            if issued_data is not None:
                # 延長回数を増加
                issued_data.extension_count += 1
                issued_data.save()

                # ユーザー情報取得
                user = issued_data.user
                user_name = user.email.split('@')[0]
                user_email = user.email
                book_title = issued_data.book.book_name

                # メールの内容を作成
                subject = "本の延長確認"
                message = f"こんにちは、{user_name}さん。\n\n{book_title}の延長を確認しました。"
                from_email = "otsuru.gity@gmail.com"  # 送信元メールアドレスを入力してください
                to_email = user_email

                # メールを送信する
                try:
                    send_mail(subject, message, from_email, [to_email])
                    print("メールを送信しました。")
                except Exception as e:
                    print("メールの送信中にエラーが発生しました:", e)

        elif 'update_qr_button' in request.POST:
            # QRコードを更新する
            make_qr(request.user)
            return HttpResponseRedirect('/')

    # レンタル中のIssuedDataを取得
    issued_data = IssuedData.objects.filter(user=request.user)

    current_rental_count = 0
    issued_books = []

    for data in issued_data:
        book = data.book
        # もし返却日に記入がなければ
        if data.return_date is None:
            current_rental_count += 1
            issued_books.append({
                'book_name': book.book_name,
                'extension_count': data.extension_count,
                'issue_date': data.rental_date,
                'return_date': data.rental_date + timedelta(weeks=max(0, 2 + data.extension_count)),
                'id': data.book.bar_code
            })

    # ユーザーのQRコードURLを取得
    qr_code_url = request.user.QRcode
    if qr_code_url:
        qr_code_url = qr_code_url.url.replace('/static/', '/')

    # テンプレートに渡すパラメータを設定
    params = {
        'user_email': request.user.email.split('@')[0],
        'current_rental_count': current_rental_count,
        'issued_books': issued_books,
        'session_age_minutes': session_age // 60,  # セッションの有効期限を分に変換
        'qr_code_url': qr_code_url
    }
    print('QRcode:' + str(request.user.QRcode) + '\n')

    # ホームページをレンダリングして返す
    return render(request, 'library/home.html', params)

"""
関数: user_history
    ユーザーの書籍レンタル履歴を取得し、テンプレートに渡すための関数。
引数:
    request: HTTPリクエストオブジェクト。ユーザー情報を含む。
戻り値:
    テンプレートにユーザー名とレンタル履歴を渡したHTTPレスポンス。
"""
@login_required(login_url='/login')
def user_history(request):
    # ユーザー名をメールアドレスのローカル部分から取得
    username = request.user.email.split('@')[0]

    # ユーザーに関連するレンタルデータを取得し、レンタル日で降順にソート
    issued_data = IssuedData.objects.filter(user=request.user).order_by('-rental_date')
    
    # レンタル履歴を格納するリストを初期化
    issued_books = []
    
    # 各レンタルデータに対して処理
    for data in issued_data:
        book = data.book
        # 返却済の場合
        if data.return_date:
            issued_books.append({
                'book_name': book.book_name,
                'issue_date': data.rental_date,
                'return_date': data.return_date,
                'status': '返却済'
            })
        # レンタル中の場合
        elif data.return_date is None:
            issued_books.append({
                'book_name': book.book_name,
                'issue_date': data.rental_date,
                'return_date': '',
                'status': 'レンタル中'
            })
    
    # テンプレートに渡すコンテキストを作成
    context = {
        'username': username,
        'user_issued_data': issued_books,
    }

    # 'library/user_history.html' テンプレートをレンダリングしてレスポンスを返す
    return render(request, 'library/user_history.html', context)

"""
関数: book_list
    書籍の一覧を表示し、検索機能とページネーションを提供するための関数。
引数:
    request: HTTPリクエストオブジェクト。ユーザー情報とフォームデータを含む。
    page_num: 現在のページ番号。
戻り値:
    テンプレートに書籍データ、メッセージ、検索フォームを渡したHTTPレスポンス。
"""
@login_required(login_url='/login')
def book_list(request, page_num):
    # すべての書籍データをID順に取得
    data = Book.objects.all().order_by('id')
    
    # POSTデータがある場合はフォームを初期化
    form = SearchBookForm(request.POST or None)
    paginated_data = None
    msg = ''
    
    # POSTリクエストの場合、検索処理を実行
    if request.method == 'POST':
        # フォームが有効な場合の処理
        if form.is_valid():
            # フォームから検索語句を取得
            find = form.cleaned_data.get('find')
            
            # 検索条件を適用し、データをフィルタリング
            data = data.filter(Q(author_name__contains=find) |
                               Q(book_name__contains=find) |
                               Q(id__contains=find))
            
            # 検索結果の件数をメッセージとして設定
            msg = f'Result: {data.count()}'
    
    # ページネーションを設定（1ページあたり10件）
    paginator = Paginator(data, 10)
    
    # ページネーションされたデータを取得
    paginated_data = paginator.get_page(page_num)
    
    # テンプレートに渡すパラメータを作成
    params = {
        'data': paginated_data,
        'message': msg,
        'form': form,
    }
    
    # 'library/book_list.html' テンプレートをレンダリングしてレスポンスを返す
    return render(request, 'library/book_list.html', params)

# Bookモデル ListView:全リスト DetailView:個々の詳細
class BookList(ListView):
    model = Book
    template_name = 'library/book_list.html'
    paginate_by = 10  # ページネーションを追加
    context_object_name = 'data'
    
    def get_queryset(self):
        # データをidの昇順で取得
        queryset = super().get_queryset()
        return queryset.order_by('id')

# Bookモデルの詳細表示
class BookDetail(DetailView):
    model = Book

"""
関数: want_book
    ユーザーが欲しい本の情報を入力し、国立国会図書館サーチAPIとAmazon APIを使用して詳細情報を取得し保存する関数。
引数:
    request: HTTPリクエストオブジェクト。ユーザー情報とフォームデータを含む。
戻り値:
    テンプレートにフォームと書籍リストを渡したHTTPレスポンス。
"""
@login_required(login_url='/login')
def want_book(request):
    # POSTリクエストの場合、フォームデータを処理
    if request.method == 'POST':
        form = WantBookForm(request.POST)
        
        # フォームが有効な場合の処理
        if form.is_valid():
            # フォームから本のオブジェクトを作成（まだ保存しない）
            book = form.save(commit=False)
            book.user = request.user  # 現在のユーザーを関連付け
            
            # 本の情報をデータベースに保存
            book.save()
            
            # 書籍一覧ページにリダイレクト
            return redirect('want_book')
    else:
        # GETリクエストの場合、新しいフォームを作成
        form = WantBookForm()
    
    # データベースからすべての本を取得
    want_books = Want_Book.objects.all()

    # テンプレートにフォームと本のリストを渡す
    return render(request, 'library/want_book.html', {'form': form, 'books': want_books})


# 他サイトQRコード登録用

"""
関数: registration
    ユーザーの他サイトQRコード情報を取得し、テンプレートに渡すための関数。
引数:
    request: HTTPリクエストオブジェクト。ユーザー情報を含む。
戻り値:
    テンプレートにQRコード情報を渡したHTTPレスポンス。
"""
@login_required(login_url='/login')
def registration(request):
    # 現在のユーザーを取得
    user = request.user
    
    # ユーザーに関連するQRコードを取得
    qr_code = QRCode.objects.filter(user=user).first()
    
    # QRコードのデータを格納するリストを初期化
    qr_data = []
    
    # QRコードが存在する場合の処理
    if qr_code:
        # LINEコードが未登録でInstagramコードが登録されている場合
        if qr_code.line_code is None and qr_code.instagram_code is not None:
            qr_data.append({
                'line_code': '未登録',
                'instagram_code': qr_code.instagram_code
            })
        # Instagramコードが未登録でLINEコードが登録されている場合
        elif qr_code.instagram_code is None and qr_code.line_code is not None:
            qr_data.append({
                'line_code': qr_code.line_code,
                'instagram_code': '未登録'
            })
        # 両方のコードが未登録の場合
        elif qr_code.line_code is None and qr_code.instagram_code is None:
            qr_data.append({
                'line_code': '未登録',
                'instagram_code': '未登録'
            })
        # 両方のコードが登録されている場合
        else:
            qr_data.append({
                'line_code': qr_code.line_code,
                'instagram_code': qr_code.instagram_code
            })
    
    # テンプレートに渡すコンテキストを作成
    context = {
        'qr_data': qr_data,
    }
    
    # 'library/registration.html' テンプレートをレンダリングしてレスポンスを返す
    return render(request, 'library/registration.html', context)

"""
関数: qr_registration
    ユーザーのQRコード情報をInstagramまたはLineのIDで更新するための関数。
引数:
    request: HTTPリクエストオブジェクト。ユーザー情報とQRコードデータを含む。
戻り値:
    QRコード登録ページへのリダイレクトまたはテンプレートをレンダリングしたHTTPレスポンス。
"""
@csrf_exempt
@login_required(login_url='/login')
def qr_registration(request):
    # POSTリクエストの場合、QRコード情報を処理
    if request.method == 'POST':
        # リクエストボディからJSONデータを読み込む
        data = json.loads(request.body)
        user_id = data.get('user_id')
        sitename = data.get('sitename')
        
        # デバッグ用にユーザーIDとサイト名を出力
        print(user_id)
        print(sitename)

        # サイト名に応じてQRコード情報を更新
        user = request.user
        qr_code = QRCode.objects.filter(user=user).first()
        
        if sitename == "www.instagram.com":
            # Instagramの場合の処理
            qr_code.instagram_code = user_id
            qr_code.save()
        elif sitename == "line.me":
            # Lineの場合の処理
            qr_code.line_code = user_id
            qr_code.save()
        
        # QRコード登録ページへのリダイレクト
        return redirect('/library/qr_registration')  # リダイレクト先を適切なビューに変更してください

    # GETリクエストの場合、QRコード登録ページをレンダリング
    return render(request, 'library/qr_registration.html')

# 貸し借り管理用

# カメラ(バーコード)ストリーミングページの表示
def camera_barcode(request):
    return render(request, 'library/camera_barcode.html')

# QRコードカメラページの表示
def camera_qr(request):
    return render(request, 'library/camera_qr.html')

"""
関数: book_rental
    ユーザーが書籍をレンタルする際の処理を行い、必要に応じてメール通知を送信する関数。
引数:
    request: HTTPリクエストオブジェクト。ユーザー情報と書籍情報を含む。
戻り値:
    レンタル処理後のリダイレクトまたはエラーメッセージを含むHTTPレスポンス。
"""
@csrf_exempt
@rate_limit(rate=1, per=5)
def book_rental(request):
    # POSTリクエストの場合、レンタル処理を実行
    if request.method == 'POST':
        # リクエストボディをデバッグ用に出力
        print("Request body:", request.body.decode('utf-8'))
        
        try:
            # リクエストボディからJSONデータを読み込む
            request_body = json.loads(request.body.decode('utf-8'))
            
            # user_idとbook_idを取得
            user_id = request_body.get('user_id')
            book_id = request_body.get('book_id')

            # 取得したuser_idとbook_idを出力
            print("User ID:", user_id)
            print("Book ID:", book_id)
            
            # 書籍とユーザーをデータベースから取得
            book = Book.objects.get(bar_code=book_id)
            user = QRCode.objects.get(url=user_id).user
        except (Book.DoesNotExist, QRCode.DoesNotExist):
            # 書籍またはユーザーが見つからない場合のエラーメッセージ
            return HttpResponse("指定されたバーコードまたはユーザーが見つかりませんでした。")
        
        # もし未返却のレンタルデータがある場合、返却処理を行う
        try:
            issued_data = IssuedData.objects.filter(book=book, return_date=None).first()
            if issued_data:
                issued_data.return_date = timezone.now()
                issued_data.save()
        except Exception as e:
            # 例外が発生した場合のエラーメッセージ
            print("エラーが発生しました:", e)
        
        # 新しいレンタルデータを作成
        rental_date = timezone.now().date()
        issued_data = IssuedData(user=user, book=book, rental_date=rental_date)
        issued_data.save()
        # デバッグ用
        # print('レンタルしました')
        
        # ユーザー情報を取得
        user_name = user.email.split('@')[0]
        user_email = user.email
        book_title = book.book_name 

        # メールの内容を作成
        subject = "本のレンタル確認"
        message = f"こんにちは、{user_name}さん。\n\n{book_title}をレンタルしました。返却期間は2週間です。"
        from_email = "otsuru.gity@gmail.com"  # 送信元メールアドレスを入力してください
        to_email = user_email
        
        # メールを送信する
        try:
            send_mail(subject, message, from_email, [to_email])
            # デバッグ用
            # print("メールを送信しました。")
        except Exception as e:
            # メール送信中にエラーが発生した場合のエラーメッセージ
            print("メールの送信中にエラーが発生しました:", e)
        
        # レンタル処理後のリダイレクト
        return redirect('/camera_qr')

    # POST以外のリクエストに対するエラーメッセージ
    return HttpResponse("このエンドポイントはPOSTリクエストのみ受け付けます。")

"""
関数: book_return
    ユーザーが書籍を返却する際の処理を行い、必要に応じてメール通知を送信する関数。
引数:
    request: HTTPリクエストオブジェクト。書籍情報を含む。
戻り値:
    返却処理後のリダイレクトまたはエラーメッセージを含むHTTPレスポンス。
"""

# CSRFトークンを無効化し、レート制限を適用するデコレータ
@csrf_exempt
@rate_limit(rate=1, per=5)
def book_return(request):
    # POSTリクエストの場合、返却処理を実行
    if request.method == 'POST':
        try:
            # リクエストボディからJSONデータを読み込む
            request_body = json.loads(request.body.decode('utf-8'))
            book_id = request_body.get('book_id')
            
            # バーコードに基づいて書籍をデータベースから取得
            book = Book.objects.get(bar_code=book_id)
        except Book.DoesNotExist:
            # 書籍が見つからない場合のエラーメッセージ
            return HttpResponse("指定されたバーコードに対応する書籍は見つかりませんでした。")
        
        # 未返却のレンタルデータを取得
        issued_data = IssuedData.objects.filter(book=book, return_date=None).first()
        if issued_data:
            # 返却日を設定し、データを保存
            issued_data.return_date = timezone.now()
            issued_data.save()
            # デバッグ用
            # print('返却しました')
        
            # ユーザー情報を取得
            user_name = issued_data.user.email.split('@')[0]
            user_email = issued_data.user.email
            book_title = issued_data.book.book_name 
        
            # メールの内容を作成
            subject = "本の返却確認"
            message = f"こんにちは、{user_name}さん。\n\n{book_title}の返却を確認しました。"
            from_email = "otsuru.gity@gmail.com"  # 送信元メールアドレスを入力してください
            to_email = user_email

            # メールを送信する
            try:
                send_mail(subject, message, from_email, [to_email])
                # デバッグ用
                # print("メールを送信しました。")
            except Exception as e:
                # メール送信中にエラーが発生した場合のエラーメッセージ
                print("メールの送信中にエラーが発生しました:", e)
        
        # 返却処理後のリダイレクト
        return redirect('/camera_qr')

    # POST以外のリクエストに対するエラーメッセージ
    return HttpResponse("このエンドポイントはPOSTリクエストのみ受け付けます。")

# 運営用

# 本登録用
@user_passes_test(is_superuser, login_url='/login')
def qr_reading(request):
    return render(request, 'qr_reading.html')

"""
関数: book_create
    新しい書籍を登録するためのフォームを提供し、Google Books APIから書籍情報を取得する関数。
引数:
    request: HTTPリクエストオブジェクト。書籍情報を含む。
戻り値:
    書籍登録後のリダイレクトまたはテンプレートをレンダリングしたHTTPレスポンス。
"""
@csrf_exempt
@user_passes_test(is_superuser, login_url='/login')
def book_create(request):
    # "save"ボタンが押された場合の処理
    if "save" in request.POST:
        form = BookForm(request.POST)
        # フォームが有効な場合、書籍を保存
        if form.is_valid():
            form.save()
            messages.success(request, '書籍が正常に登録されました。')
            # 書籍管理ページにリダイレクト
            return redirect(to='/book_manage/1')
    else:
        book_info = None
        obj = None  # 初期化
    
        # POSTリクエストの場合、バーコードとQRコードを処理
        if request.method == 'POST':
            try:
                request_body = json.loads(request.body.decode('utf-8'))
                # barcodeとqrcodeを取得
                barcode = request_body.get('barcode')
                qrcode = request_body.get('qrcode')
                print("BarCode:", barcode)
                print("QrCode:", qrcode)
            except (Book.DoesNotExist, QRCode.DoesNotExist):
                # バーコードまたはQRコードが見つからない場合のエラーメッセージ
                return HttpResponse("バーコードまたはQRコードが見つかりませんでした。")
        
            # Google Books APIから書籍情報を取得
            book_info = get_book_info(barcode)
            if book_info:
                # 取得した書籍情報を出力
                print("book_name:", book_info['book_name'])
                print("author_name:", ', '.join(book_info['author_name']))
                print("description:", book_info['description'])
                print("image_link:", book_info['image_link'])
                print("bar_code:", qrcode)

        # 書籍情報がJSON形式で要求された場合
        if request.headers.get('Content-Type') == 'application/json':
            if book_info:
                # 書籍情報をJSON形式で返す
                book_info_json = {
                    'book_name': book_info['book_name'],
                    'author_name': ', '.join(book_info['author_name']),
                    'description': book_info['description'],
                    'image_link': book_info['image_link'],
                    'bar_code': qrcode
                }
                return JsonResponse(book_info_json)

    # テンプレートに渡すパラメータを作成
    params = {
        'title': 'New Book',
        'form': BookForm(),
    }
    
    # 'library/book_create.html' テンプレートをレンダリングしてレスポンスを返す
    return render(request, 'library/book_create.html', params)

"""
関数: get_book_info
    Google Books APIを使用して、指定されたバーコードに対応する本の情報を取得する関数。
引数:
    barcode: 本のISBNバーコード。
戻り値:
    本の情報を含む辞書。情報が取得できない場合はNoneを返す。
"""
def get_book_info(barcode):
    # Google Books APIにアクセスして本の情報を取得
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{barcode}"
    response = requests.get(url)
    
    # APIリクエストが成功した場合
    if response.status_code == 200:
        data = response.json()
        
        # 'items'キーが存在する場合、最初の本の情報を取得
        if 'items' in data:
            item = data['items'][0]
            book_info = {
                'book_name': item['volumeInfo']['title'],
                'author_name': item['volumeInfo'].get('authors', []),
                'description': item['volumeInfo'].get('description', ''),
                'image_link': item['volumeInfo'].get('imageLinks', {}).get('thumbnail', ''),
            }
            return book_info
    
    # 情報が取得できなかった場合
    return None

"""
関数: book_delete
    指定されたIDの書籍を削除するための関数。
引数:
    request: HTTPリクエストオブジェクト。書籍削除のリクエストを含む。
    num: 削除対象の書籍ID。
戻り値:
    書籍削除後のリダイレクトまたは削除確認ページをレンダリングしたHTTPレスポンス。
"""
@user_passes_test(is_superuser, login_url='/login')
def book_delete(request, num):
    # 指定されたIDの書籍を取得
    book = Book.objects.get(id=num)
    
    # POSTリクエストを受けた場合、書籍を削除して書籍一覧にリダイレクト
    if request.method == 'POST':
        book.delete()
        return redirect(to='/book_manage/1')
    
    # 削除確認ページに渡すパラメータを作成
    params = {
        'title': 'Delete Book',
        'id': num,
        'obj': book,
    }
    
    # 'library/Book_delete.html' テンプレートをレンダリングしてレスポンスを返す
    return render(request, 'library/Book_delete.html', params)

"""
関数: book_manage
    書籍管理ページを表示し、新しい書籍の追加やQRコードの生成を行うための関数。
引数:
    request: HTTPリクエストオブジェクト。書籍情報やQRコード生成リクエストを含む。
    page_num: 現在のページ番号（デフォルトは1）。
戻り値:
    書籍管理ページをレンダリングしたHTTPレスポンス。
"""
@user_passes_test(is_superuser, login_url='/login')
def book_manage(request, page_num=1):
    # すべての書籍データを取得し、ID順に並べ替え
    data = Book.objects.all().order_by('id')
    
    # POSTデータがある場合はフォームを初期化
    form = SearchBookForm(request.POST or None)
    msg = ''

    # POSTリクエストの場合
    if request.method == 'POST':
        if form.is_valid():
            # フォームが有効な場合、書籍を保存
            form.save()
            msg = 'Book added successfully.'
        
        # QRコード生成のPOSTリクエストを処理
        if 'num_qr' in request.POST:
            num_qr = int(request.POST['num_qr'])
            
            # QRコードPDFを生成
            buffer = io.BytesIO()
            generate_qr_code_pdf(buffer, num_qr)
            buffer.seek(0)
            
            # PDFをファイルレスポンスとして返す
            return FileResponse(buffer, as_attachment=True, filename='qr_codes.pdf')
        
    # ページネーションを適用（1ページあたり10件）
    paginator = Paginator(data, 10)
    paginated_data = paginator.get_page(page_num)
    
    # テンプレートに渡すパラメータを設定
    params = {
        'title': 'Book Management',
        'form': form,
        'message': msg,
        'data': paginated_data,
    }
    
    # 'library/Book_manage.html' テンプレートをレンダリングして返す
    return render(request, 'library/Book_manage.html', params)

"""
関数: user_manage
    ユーザー管理ページを表示し、ユーザーの貸出情報を管理するための関数。
引数:
    request: HTTPリクエストオブジェクト。ユーザー情報や検索リクエストを含む。
    page_num: 現在のページ番号（デフォルトは1）。
戻り値:
    ユーザー管理ページをレンダリングしたHTTPレスポンス。
"""
@user_passes_test(is_superuser, login_url='/login')
def user_manage(request, page_num=1):
    # すべての貸出データを取得
    issued_data = IssuedData.objects.all()
    
    # POSTデータがある場合はフォームを初期化
    form = SearchUserForm(request.POST or None)
    msg = ''
    
    # POSTリクエストの場合
    if request.method == 'POST':
        if form.is_valid():
            # フォームが有効な場合、検索キーワードを取得
            find = form.cleaned_data.get('find')
            
            # ユーザーのメールアドレスで絞り込み
            issued_data = IssuedData.objects.filter(user__email__icontains=find)
            
            # 検索結果の件数をメッセージとして設定
            msg = f'Result: {issued_data.count()}'
    
    # ページネーションを適用（1ページあたり10件）
    paginator = Paginator(issued_data, 10)
    paginated_data = paginator.get_page(page_num)
    
    # ユーザーデータのリストを初期化
    user_data = []
    
    # 各ユーザーの貸出データを処理
    for data in paginated_data:
        # ユーザーのメールアドレスを取得
        user_email = data.user.email.split('@')[0]
        
        # ユーザーが貸出中のデータを取得
        issued_books = IssuedData.objects.filter(user=data.user, return_date__isnull=True)
        
        # 現在の貸出数を取得
        current_rental_count = issued_books.count()
        
        # ユーザーデータリストにユーザー情報を追加
        user_data.append({
            'user_email': user_email,
            'current_rental_count': current_rental_count,
            'issued_books': issued_books,
        })
    
    # テンプレートに渡すパラメータを設定
    params = {
        'title': 'User Management',
        'message': msg,
        'form': form,
        'data': user_data,
    }
    
    # 'library/User_manage.html' テンプレートをレンダリングして返す
    return render(request, 'library/User_manage.html', params)
