# views.py
from django import forms
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.forms import AuthenticationForm 
from django.contrib.auth import login,logout, authenticate
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, FormView
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from itertools import chain
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from functools import wraps
from reportlab.pdfgen import canvas
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.core.mail import send_mail
import requests
import json
from jose import jwt
import io

from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils.http import urlencode
from django.contrib import auth
from authlib.integrations.django_client import OAuth

from .backends import make_qr
from .forms import BookForm, SearchBookForm, SearchUserForm
from .models import Book, CustomUser, IssuedData, QRCode, Want_Book
from .qr import generate_qr_code_pdf

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

def login_op(request):
    """
    API to login to OP
    """
    # Djangoのセッションを削除するためには、以下のようにします
    if 'session_key' in request.session:
        del request.session['session_key']
        
    print('##############################')
    redirect_uri = request.build_absolute_uri(
        reverse_lazy('login_rp')
    )
    print(redirect_uri)
    # keep next url because it gets lost when token response occurs
    if 'next' in request.GET:
        request.session['url_next_to_login'] = request.GET['next']

    # authentication request
    return OAUTH.rp.authorize_redirect(request, redirect_uri)


def login_rp(request):
    """
    Redirect endpoint which makes session with RP
    """
    if 'error' in request.GET:
        err_msg = request.GET['error_description']
        # error handling
        return HttpResponse(err_msg)
    
    
    print(OAUTH.rp)
    print(request)
    
    user = auth.authenticate(request, client=OAUTH.rp)
    print(user)
    print("OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
    if user is not None and user.is_authenticated:
        auth.login(request, user)

        redirect_url = request.session.get('url_next_to_login', settings.LOGIN_REDIRECT_URL)
        if 'url_next_to_login' in request.session:
            del request.session['url_next_to_login']

        return redirect(redirect_url)
    
    """
    # Fetch the access token using the code returned from the authorization endpoint
    token = OAUTH.rp.authorize_access_token(request)
    if token:
        # Use the access token to fetch user information
        user_info = OAUTH.rp.parse_id_token(request, token)
        # Check if the user exists and authenticate them
        user = authenticate(request, user_info=user_info)
        if user is not None and user.is_authenticated:
            # Log in the user
            auth.login(request, user)
            # Redirect the user to the desired page
            redirect_url = request.session.get('url_next_to_login', settings.LOGIN_REDIRECT_URL)
            if 'url_next_to_login' in request.session:
                del request.session['url_next_to_login']
            return redirect(redirect_url)
    """
    print("###############################s")
    print(user)

    # this is a test code. write error handling.
    return HttpResponse('error')

def get_user_email(access_token):
    # Keycloakのトークン検証用のエンドポイントURL
    token_introspection_url = 'https://your-keycloak-domain/auth/realms/your-realm/protocol/openid-connect/token/introspect'
    
    # KeycloakのクライアントIDとクライアントシークレット
    client_id = ''           #your-client-id
    client_secret = ''       #your-client-secret

    # トークンの検証
    response = requests.post(
        token_introspection_url,
        data={'token': access_token, 'client_id': client_id, 'client_secret': client_secret}
    )

    if response.status_code == 200:
        token_info = response.json()

        # トークンが有効かどうかを確認
        if token_info['active']:
            # トークンが有効な場合、トークンをデコードしてユーザーの情報にアクセス
            decoded_token = jwt.decode(access_token, algorithms=['RS256'], options={'verify_at_hash': False})
            # ユーザーのメール情報を取得
            user_email = decoded_token['email']
            return user_email
        else:
            # トークンが無効の場合はエラーを返すなどの処理
            return None
    else:
        # エラーが発生した場合はエラーを返すなどの処理
        return None
    
"""
# アプリケーションでKeycloakから取得したトークン
access_token = 'your-access-token'

# ユーザーのメール情報を取得
user_email = get_user_email(access_token)
print("User email:", user_email)
"""

@login_required(login_url='/library/login/')
def registration(request):
    user = request.user
    qr_code = QRCode.objects.filter(user=user).first()
    
    qr_data = []
    if qr_code:
        if qr_code.line_code is None and qr_code.instagram_code is not None:
            qr_data.append({
                'line_code': '未登録',
                'instagram_code': qr_code.instagram_code
            })
        elif qr_code.instagram_code is None and qr_code.line_code is not None:
            qr_data.append({
                'line_code': qr_code.line_code,
                'instagram_code': '未登録'
            })
        elif qr_code.line_code is None and qr_code.instagram_code is None:
            qr_data.append({
                'line_code': '未登録',
                'instagram_code': '未登録'
            })
        else:
            qr_data.append({
                'line_code': qr_code.line_code,
                'instagram_code': qr_code.instagram_code
            })
            
    context = {
        'qr_data': qr_data,
    }
    return render(request, 'library/registration.html', context)

#########################################################################################################
#########################################################################################################
#########################################################################################################
@login_required
def want_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.user = request.user
            
            # 国立国会図書館サーチAPIから書籍情報を取得
            title = book.title
            url = f'https://ndlsearch.ndl.go.jp/api/sru?operation=searchRetrieve&query=title={title}&maximumRecords=1&recordSchema=dcndl_simple'
            response = requests.get(url)
            data = response.text
            parser = xml.etree.ElementTree.fromstring(data)
            record = parser.find('.//{http://www.loc.gov/zing/srw/}record')
            
            if record:
                title_element = record.find('.//{http://purl.org/dc/elements/1.1/}title')
                author_element = record.find('.//{http://purl.org/dc/elements/1.1/}creator')
                cover_element = record.find('.//{http://ndl.go.jp/dcndl/terms/}coverurl')
                
                book.title = title_element.text if title_element else ''
                book.author = author_element.text if author_element else ''
                book.cover_url = cover_element.text if cover_element else ''
            
            # Amazon Product Advertising APIから購入リンクを取得
            url = f'https://webservices.amazon.co.jp/paapi5/searchitems?title={book.title}&author={book.author}&SearchIndex=Books'
            response = requests.get(url)
            data = response.json()
            
            if data['SearchResult'] and data['SearchResult']['Items']:
                item = data['SearchResult']['Items'][0]
                book.purchase_link = item['DetailPageURL']
            
            book.save()
            return redirect('library/want_book')
    else:
        form = BookForm()
    
    books = Book.objects.all()
    return render(request, 'library/want_book.html', {'form': form, 'books': books})

# ログインが必要なページであることを示すデコレータ
@csrf_exempt
@login_required(login_url='library/login/')
def qr_registration(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        sitename = data.get('sitename')
        print(user_id)
        print(sitename)

        if sitename == "www.instagram.com":
            # Instagramの場合の処理
            user = request.user
            qr_code = QRCode.objects.filter(user=user).first()
            qr_code.instagram_code = user_id
            qr_code.save()
        elif sitename == "line.me":
            # Lineの場合の処理
            user = request.user
            qr_code = QRCode.objects.filter(user=user).first()
            qr_code.line_code = user_id
            qr_code.save()
            
        return redirect('qr_registration')  # リダイレクト先を適切なビューに変更してください

    return render(request, 'library/qr_registration.html')

def rate_limit(rate, per):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            key = f'{func.__name__}:{request.META["REMOTE_ADDR"]}'
            count = cache.get(key, 0)
            if count >= rate:
                return HttpResponse("Too Many Requests", status=429)
            cache.set(key, count + 1, per)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

# qrログイン用 (ワンチャン不要)
def qr_code_login(request):
    if request.method == 'POST':
        qr_data = request.POST.get('qr_data')
        user = authenticate(request, qr_data=qr_data)
        if user is not None:
            login(request, user)
            return redirect('library/camera_qr.html') 
        else:
            return redirect('library/qr_login.html') 
    else:
        return render(request, 'library/qr_login.html')
    
# スーパーユーザーのみがアクセスできるようにするデコレータ
def is_superuser(user):
    return user.is_authenticated and user.is_superuser

# Emailを使用した認証フォーム
class EmailAuthenticationForm(AuthenticationForm):
    email = forms.EmailField(
        max_length=254,
        widget=forms.TextInput(attrs={'autofocus': True}),
    )

    def __init__(self, *args, **kwargs):
        super(EmailAuthenticationForm, self).__init__(*args, **kwargs)
        # ユーザー名を非表示にする
        self.fields['username'].widget = forms.HiddenInput()
        self.fields['username'].required = False

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        print(email)
        print(password)

        if email and password:
            # 提供されたメールアドレスとパスワードを使用して認証する
            user = authenticate(self.request, email=email, password=password)

            if user is not None:
                # 認証が成功したらユーザーをログインさせる
                login(self.request, user)

                # ログイン成功後にリダイレクトするURLを指定
                next_url = self.request.GET.get('next', '/library/')

                # デバッグメッセージ
                print(f"Redirecting to {next_url}")
                return redirect('/library/')
            else:
                # デバッグメッセージの表示
                print("Authentication failed for email:", email)
                # 無効なメールアドレスまたはパスワードの場合、'email'フィールドにエラーを追加する
                self.add_error('email', '正しいメールアドレスとパスワードを入力してください。なお、両方のフィールドは大文字と小文字を区別する場合があります。')

        # 非表示フィールドのためのクリーンデータ
        self.cleaned_data.pop('username', None)
        self.cleaned_data.pop('password', None)

        return self.cleaned_data

# ログインビュー
def login_view(request):
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('/library/')
    else:
        form = EmailAuthenticationForm(request)

    return render(request, 'library/user_login.html', {'form': form})

# ログアウトビュー
def logout_view(request):
    logout(request)
    
    # Keycloakのログアウトエンドポイントにリダイレクト
    keycloak_logout_url = 'https://sso.gity.co.jp/realms/gity/protocol/openid-connect/logout'
    
    #redirect_url = 'http://127.0.0.1:8000/library'
    # ログアウト後のリダイレクト先を指定（ログインページ）
    return redirect(keycloak_logout_url)# + '?redirect_uri=' + redirect_url)

# ログインが必要なページであることを示すデコレータ
@csrf_exempt
@login_required(login_url='/library/login/')
def index(request):
    # セッションの有効期限を取得（単位は秒）
    session_age = settings.SESSION_COOKIE_AGE if hasattr(settings, 'SESSION_COOKIE_AGE') else 15 * 60

    user_id = request.user.id if request.user.is_authenticated else None
    
    if request.method == 'POST':
        if 'extend_button' in request.POST:
            book_id = request.POST.get('extend_button')
            issued_data = IssuedData.objects.filter(book__bar_code=book_id, user=request.user, return_date__isnull=True).first()
            if issued_data is not None:
                issued_data.extension_count += 1
                issued_data.save()
                
                user = issued_data.user
                # ユーザー情報取得
                user_name = user.email.split('@')[0]
                user_email = user.email
                book_title =  issued_data.book.book_name
        
#####################################################################
############################################################################
                # メールの内容を作成
                subject = "本の延長確認"
                message = f"こんにちは、{user_name}さん。\n\n{book_title}の延長を確認しました。"
                from_email = "otsuru.gity@gmail.com"  # 送信元メールアドレスを入力してください                to_email = user_email
                to_email = user_email
                
                # メールを送信する
                try:
                    send_mail(subject, message, from_email, [to_email])
                    print("メールを送信しました。")
                except Exception as e:
                    print("メールの送信中にエラーが発生しました:", e)
                
        elif  'update_qr_button' in request.POST:
            # QRコードを更新するs
            make_qr(request.user)
            return HttpResponseRedirect('/library')
            
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

    qr_code_url = request.user.QRcode
    if qr_code_url:
        qr_code_url = qr_code_url.url.replace('/library/static/', '/')
        
    params = {
        'user_email': request.user.email.split('@')[0],
        'current_rental_count': current_rental_count,
        'issued_books': issued_books,
        'session_age_minutes': session_age // 60,  # セッションの有効期限を分に変換
        'qr_code_url': qr_code_url
    }
    print('QRcode:' + str(request.user.QRcode) + '\n')

    return render(request, 'library/home.html', params)

# ログインが必要なページであることを示すデコレータ
@login_required(login_url='library/login/')
def user_history(request):
    username = request.user.email.split('@')[0]

    issued_data = IssuedData.objects.filter(user=request.user).order_by('-rental_date')
    issued_books = []
    for data in issued_data:
        book = data.book
        if data.return_date:
            issued_books.append({
                'book_name': book.book_name,
                'issue_date': data.rental_date,
                'return_date': data.return_date,
                'status': '返却済'
            })
        elif data.return_date is None:
            issued_books.append({
                'book_name': book.book_name,
                'issue_date': data.rental_date,
                'return_date': '',
                'status': 'レンタル中'
            })
    context = {
        'username': username,
        'user_issued_data': issued_books,
    }

    return render(request, 'library/user_history.html', context)

# ログインが必要なページであることを示すデコレータ
@login_required(login_url='/library/login/')
def book_list(request, page_num):
    data = Book.objects.all().order_by('id')
    form = SearchBookForm(request.POST or None)  # POSTデータがある場合はフォームを初期化
    paginated_data = None
    msg = ''
    
    if request.method == 'POST':
        if form.is_valid():
            find = form.cleaned_data.get('find')  # フォームから検索語句を取得
            data = data.filter(Q(author_name__contains=find) |
                               Q(book_name__contains=find) |
                               Q(id__contains=find))  # 検索条件を適用
            msg = f'Result: {data.count()}'
    
    paginator = Paginator(data, 10)
    paginated_data = paginator.get_page(page_num)  # ページネーションされたデータを取得
    
    params = {
        'data': paginated_data,
        'message': msg,
        'form': form,
    }
    return render(request, 'library/book_list.html', params)

@csrf_exempt
@rate_limit(rate=1, per=5)
def book_rental(request):
    if request.method == 'POST':
        print("Request body:", request.body.decode('utf-8'))
        try:
            request_body = json.loads(request.body.decode('utf-8'))
            # user_idとbook_idを取得
            user_id = request_body.get('user_id')
            book_id = request_body.get('book_id')

            # 取得したuser_idとbook_idを出力
            print("User ID:", user_id)
            print("Book ID:", book_id)
            book = Book.objects.get(bar_code=book_id)
            user = QRCode.objects.get(url=user_id).user
        except (Book.DoesNotExist, QRCode.DoesNotExist):
            return HttpResponse("指定されたバーコードまたはユーザーが見つかりませんでした。")
        
        print("Request body:", request.body.decode('utf-8'))
        
        # もし未返却なら返却処理を行う
        try:
            issued_data = IssuedData.objects.filter(book=book, return_date=None).first()
            if issued_data:
                issued_data.return_date = timezone.now()
                issued_data.save()
        except Exception as e:
            # 例外が発生した場合の処理をここに記述します
            print("エラーが発生しました:", e)
                
        rental_date = timezone.now().date()
        issued_data = IssuedData(user=user, book=book, rental_date=rental_date)
        issued_data.save()
        print('レンタルしました')
        
        # ユーザー情報取得
        user_name = user.email.split('@')[0]
        user_email = user.email
        book_title = book.book_name 

############################################################################
############################################################################       
        # メールの内容を作成
        subject = "本のレンタル確認"
        message = f"こんにちは、{user_name}さん。\n\n{book_title}をレンタルしました。返却期間は2週間です。"
        from_email = "otsuru.gity@gmail.com"  # 送信元メールアドレスを入力してください
        to_email = user_email
        
        # メールを送信する
        try:
            send_mail(subject, message, from_email, [to_email])
            print("メールを送信しました。")
        except Exception as e:
            print("メールの送信中にエラーが発生しました:", e)
        
        return redirect('/library/camera_qr')

    return HttpResponse("このエンドポイントはPOSTリクエストのみ受け付けます。")

@csrf_exempt
@rate_limit(rate=1, per=5)
def book_return(request):
    if request.method == 'POST':
        try:
            request_body = json.loads(request.body.decode('utf-8'))
            book_id = request_body.get('book_id')
            book = Book.objects.get(bar_code=book_id)
        except Book.DoesNotExist:
            return HttpResponse("指定されたバーコードに対応する書籍は見つかりませんでした。")
        
        issued_data = IssuedData.objects.filter(book=book, return_date=None).first()
        if issued_data:
            issued_data.return_date = timezone.now()
            issued_data.save()
            print('返却しました')
        
            user_name = issued_data.user.email.split('@')[0]
            user_email = issued_data.user.email
            book_title = issued_data.book.book_name 
        
############################################################################
############################################################################       
            # メールの内容を作成
            subject = "本の返却確認"
            message = f"こんにちは、{user_name}さん。\n\n{book_title}の返却を確認しました。"
            from_email = "otsuru.gity@gmail.com"  # 送信元メールアドレスを入力してください
            to_email = user_email

            # メールを送信する
            try:
                send_mail(subject, message, from_email, [to_email])
                print("メールを送信しました。")
            except Exception as e:
                print("メールの送信中にエラーが発生しました:", e)
        
        
        return redirect('/library/camera_qr')

    return HttpResponse("このエンドポイントはPOSTリクエストのみ受け付けます。")

# カメラストリーミングページの表示
def camera_streaming(request):
    return render(request, 'library/camera_streaming.html')

# QRコードカメラページの表示
def camera_qr(request):
    return render(request, 'library/camera_qr.html')

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

# 以下管理者ページ
# スーパーユーザーのみがアクセスできるようにするデコレータ
@user_passes_test(is_superuser, login_url='/library/login/')
def qr_reading(request):
    return render(request, 'library/qr_reading.html')

@user_passes_test(is_superuser, login_url='/library/login/')
def choose(request):
    # 管理者用のページを表示
    return render(request, 'library/choose.html')

# スーパーユーザーのみがアクセスできるようにするデコレータ
@csrf_exempt
@user_passes_test(is_superuser, login_url='/library/login/')
def book_create(request):
    if "save" in request.POST:
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '書籍が正常に登録されました。')
            return redirect(to='/library/book_manage/1')
    else:
        book_info = None
        obj = None  # 初期化
    
        if request.method == 'POST':
            try:
                request_body = json.loads(request.body.decode('utf-8'))
                # barcodeとqrcodeを取得
                barcode = request_body.get('barcode')
                qrcode = request_body.get('qrcode')
                print("BarCode:", barcode)
                print("QrCode:", qrcode)
            except (Book.DoesNotExist, QRCode.DoesNotExist):
                return HttpResponse("バーコードまたはQRコードが見つかりませんでした。")
        
            # Google Books APIから書籍情報を取得
            book_info = get_book_info(barcode)
            if book_info:
                print("book_name:", book_info['book_name'])
                print("author_name:", ', '.join(book_info['author_name']))
                print("description:", book_info['description'])
                print("image_link:", book_info['image_link'])
                print("bar_code:", qrcode)

        # 書籍情報がJSON形式で要求された場合
        if request.headers.get('Content-Type') == 'application/json':
            if book_info:
                book_info_json = {
                    'book_name': book_info['book_name'],
                    'author_name': ', '.join(book_info['author_name']),
                    'description': book_info['description'],
                    'image_link': book_info['image_link'],
                    'bar_code': qrcode
                }
                return JsonResponse(book_info_json)

    params = {
        'title': 'New Book',
        'form': BookForm(),
    }
    
    return render(request, 'library/book_create.html', params)

def get_book_info(barcode):
    # Google Books APIにアクセスして本の情報を取得
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{barcode}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'items' in data:
            item = data['items'][0]
            book_info = {
                'book_name': item['volumeInfo']['title'],
                'author_name': item['volumeInfo'].get('authors', []),
                'description': item['volumeInfo'].get('description', ''),
                'image_link': item['volumeInfo'].get('imageLinks', {}).get('thumbnail', ''),
            }
            return book_info
    return None

# 管理者ページであることを示すデコレータ
@user_passes_test(is_superuser, login_url='/library/login/')
def choose(request):
    return render(request, 'library/choose.html')

# 管理者権限が必要なページであることを示すデコレータ
@user_passes_test(is_superuser, login_url='/library/login/')
def book_delete(request, num):
    # 指定されたIDの書籍を取得
    book = Book.objects.get(id=num)
    if(request.method == 'POST'):
        # POSTリクエストを受けた場合、書籍を削除して書籍一覧にリダイレクト
        book.delete()
        return redirect(to='/library/book_manage/1')
    params = {
        'title': 'Delete Book',
        'id': num,
        'obj': book,
    }
    return render(request, 'library/Book_delete.html', params)

# ログインが必要なページであることを示すデコレータ
@user_passes_test(lambda u: u.is_superuser, login_url='/library/login/')
def book_manage(request, page_num=1):
    """
    書籍管理ページのビュー
    """
    # すべての書籍データを取得し、ID順に並べ替え
    data = Book.objects.all().order_by('id')
    # POSTデータがある場合はフォームを初期化
    form = BookForm(request.POST or None)
    msg = ''
    
    # POSTリクエストの場合
    if request.method == 'POST':
        if form.is_valid():
            # フォームが有効な場合、書籍を保存
            form.save()
            msg = 'Book added successfully.'
        # Handle QR code generation POST request
    if request.method == 'POST' and 'num_qr' in request.POST:
        num_qr = int(request.POST['num_qr'])
        
        # Generate QR code PDF
        buffer = io.BytesIO()
        generate_qr_code_pdf(buffer, num_qr)
        buffer.seek(0)
        
        # Return PDF as file response
        return FileResponse(buffer, as_attachment=True, filename='qr_codes.pdf')
    
    # ページネーションを適用
    paginator = Paginator(data, 10)
    paginated_data = paginator.get_page(page_num)
    
    # テンプレートに渡すパラメータを設定
    params = {
        'title': 'Book Management',
        'form': form,
        'message': msg,
        'data': paginated_data,
    }
    # テンプレートをレンダリングして返す
    return render(request, 'library/Book_manage.html', params)

# スーパーユーザーのみがアクセスできるようにするデコレータ
@user_passes_test(lambda u: u.is_superuser, login_url='/library/login/')
def user_manage(request, page_num=1):
    """
    ユーザー管理ページのビュー
    """
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
            msg = f'Result: {issued_data.count()}'
    
    # ページネーションを適用
    paginator = Paginator(issued_data, 10)
    paginated_data = paginator.get_page(page_num)
    
    # ユーザーデータのリストを初期化
    user_data = []
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
    # テンプレートをレンダリングして返す
    return render(request, 'library/User_manage.html', params)
