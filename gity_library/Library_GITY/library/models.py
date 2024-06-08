# models.py

from django.db import models
from datetime import date
from django.utils import timezone

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def create_user(self, email, **extra_fields):
        # ユーザーを作成するカスタムマネージャーのメソッド
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
            
        user.save(using=self._db)
        return user
        
    def create_superuser(self, email, password, **extra_fields):
        # スーパーユーザーを作成するカスタムマネージャーのメソッド
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    # カスタムユーザーモデル、email をユニークな識別子として使用
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    QRcode = models.ImageField(upload_to="static/image/",null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class Book(models.Model):
    # 本の情報を保持するモデル
    # 本の名前
    book_name = models.CharField(max_length=150)

    # 著者の名前
    author_name = models.CharField(max_length=200)
    
    # 本のバーコード
    bar_code = models.IntegerField(default=0000000000000)

    # 本のあらすじ
    description = models.TextField(blank=True)

    # 本の画像リンク
    image_link = models.URLField(blank=True)
    
    # 利用可能な数量
    quantity = models.IntegerField(default=1)

    # 本が追加された日付（デフォルトは今日の日付）
    book_add_date = models.DateField(default=timezone.now)
    
    def __str__(self):
        return f'<book id={self.id}, {self.book_name}({self.quantity})>'

class IssuedData(models.Model):
    # CustomUser モデルとの関連を表す ForeignKey
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    # Book モデルとの関連を表す ForeignKey
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)

    # 本が貸し出された日付
    rental_date = models.DateField(default=timezone.now, null=True, blank=True)

    # 本が返却される予定の日付
    return_date = models.DateField(null=True, blank=True)
    
    # 延長回数
    extension_count = models.IntegerField(default=0)
    
    @property
    def username(self):
        # 関連するユーザーの email からユーザー名を取得するプロパティ
        return self.user.email.split('@')[0]

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
    # CustomUser モデルとの関連を表す ForeignKey
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    url = models.CharField(max_length=200)
    
    line_code = models.CharField(max_length=200, null=True, blank=True)
    
    instagram_code = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        username = self.user.email.split('@')[0]
        return f"{username}\n{self.url}"

class Want_Book(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    purchase_link = models.URLField()
    reason = models.TextField()
    purchaser = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchased_books')
    
    def __str__(self):
        return self.title