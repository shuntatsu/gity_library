# models.py

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    """ 
    関数: create_user
        新しいユーザーを作成するメソッド
    引数:
        email: ユーザーのメールアドレス
        extra_fields: その他の追加フィールド
    """
    
    def create_user(self, email, password=None, **extra_fields):
        # ユーザーを作成するカスタムマネージャーのメソッド
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password) 
        user.save(using=self._db)
        return user

    """
    関数: create_superuser
        新しいスーパーユーザーを作成するメソッド
    引数:
        email: スーパーユーザーのメールアドレス
        password: スーパーユーザーのパスワード
        extra_fields: その他の追加フィールド
    """
    def create_superuser(self, email, password, **extra_fields):
        # スーパーユーザーを作成するカスタムマネージャーのメソッド
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """ 
    モデル: CustomUser
        カスタムユーザーモデル、email をユニークな識別子として使用
    フィールド:
        email: ユーザーのメールアドレス（ユニーク）
        is_active: ユーザーがアクティブかどうか
        is_staff: ユーザーがスタッフかどうか
        QRcode: ユーザーのQRコード画像
    """

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    QRcode = models.ImageField(upload_to="static/image/", null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class Book(models.Model):
    """ 
    モデル: Book
        本の情報を保持するモデル
    フィールド:
        book_name: 本の名前
        author_name: 著者の名前
        bar_code: 本のバーコード
        description: 本のあらすじ
        image_link: 本の画像リンク
        quantity: 利用可能な数量
        book_add_date: 本が追加された日付
    """

    book_name = models.CharField(max_length=150)
    author_name = models.CharField(max_length=200)
    bar_code = models.IntegerField(default=0000000000000)
    description = models.TextField(blank=True)
    image_link = models.URLField(blank=True)
    quantity = models.IntegerField(default=1)
    book_add_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f'<book id={self.id}, {self.book_name}({self.quantity})>'

class IssuedData(models.Model):
    """
    モデル: IssuedData
        本の貸し出しデータを保持するモデル
    フィールド:
        user: 貸し出しを行ったユーザー
        book: 貸し出された本
        rental_date: 本が貸し出された日付
        return_date: 本が返却される予定の日付
        extension_count: 延長回数
    """

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)
    rental_date = models.DateField(default=timezone.now, null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    extension_count = models.IntegerField(default=0)

    @property
    def username(self):
        # 関連するユーザーの email からユーザー名を取得するプロパティ
        return self.user.email.split('@')[0]

    """
    関数: save
        IssuedData インスタンスを保存するメソッド
    引数:
        args: 引数のリスト
        kwargs: キーワード引数の辞書
    """
    def save(self, *args, **kwargs):
        # IssuedData インスタンスを保存する際に本の数量を処理するメソッド
        if not self.pk:
            self.book.quantity -= 1
            self.book.save()

        elif self.return_date:
            self.book.quantity += 1
            self.book.save()

        super().save(*args, **kwargs)

    def __str__(self):
        username = self.user.email.split('@')[0]
        books_issued = f"{self.book.book_name} ({self.extension_count})" if self.book else ''
        return f"{username}\n{books_issued}\nIssue Date: {self.rental_date}"

class QRCode(models.Model):
    """ 
    モデル: QRCode
        ユーザーのQRコード情報を保持するモデル
    フィールド:
        user: QRコードに関連するユーザー
        url: QRコードのURL
        line_code: LINEコード
        instagram_code: Instagramコード
    """

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    url = models.CharField(max_length=200)
    line_code = models.CharField(max_length=200, null=True, blank=True)
    instagram_code = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        username = self.user.email.split('@')[0]
        return f"{username}\n{self.url}"

class Want_Book(models.Model):
    """
    モデル: Want_Book
        ユーザーが欲しい本の情報を保持するモデル
    フィールド:
        user: 本を欲しいと希望するユーザー
        title: 本のタイトル
        author: 著者の名前
        purchase_link: 購入リンク
        reason: 欲しい理由
        purchaser: 本を購入したユーザー
    """

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    purchase_link = models.URLField()
    reason = models.TextField()
    purchaser = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchased_books')
    want_count = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.title