# admin.py

from django.contrib import admin
from .models import Book, IssuedData, CustomUser, QRCode, Want_Book
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm

# BookモデルとIssuedDataモデルを管理者ページに登録
admin.site.register(Book)
admin.site.register(IssuedData)
admin.site.register(QRCode)
admin.site.register(Want_Book)

# カスタムユーザーモデルの管理者クラスを定義
class CustomUserAdmin(UserAdmin):
    # カスタムユーザーの追加フォームを指定
    add_form = CustomUserCreationForm
    
    # 管理者ページに表示するフィールドを指定
    list_display = ('email', 'is_active', 'is_staff', 'QRcode')  # 'email'を表示に追加
    
    # ユーザーの一覧を 'email' でソート
    ordering = ('email',)  # 'email'を基準にソート

    # 'username' フィールドに関する設定を削除して 'email' と 'password' だけを表示
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login',)}),
    )

    # ユーザーの追加フォームに関する設定
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )

# カスタムユーザーモデルとその管理者クラスを管理者ページに登録
admin.site.register(CustomUser, CustomUserAdmin)