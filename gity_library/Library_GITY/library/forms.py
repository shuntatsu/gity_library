from django import forms
from .models import Book, CustomUser
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

# 書籍検索フォーム
class SearchBookForm(forms.Form):
    find = forms.CharField(label='Find', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

# ユーザー検索フォーム
class SearchUserForm(forms.Form):
    find = forms.CharField(label='Find', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

# 書籍バーコード入力フォーム
class BookBarCodeForm(forms.Form):
    bar_code = forms.IntegerField(label='Bar Code')

# 書籍フォーム（モデルフォーム）
class BookForm(forms.ModelForm):
    class Meta:
        model = Book  # フォームの対象となるモデルを指定
        fields = '__all__'  # すべてのフィールドを使用

# ユーザー作成フォーム（カスタム）
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # パスワードフィールドを必須ではなくする
        self.fields['password1'].required = False
        self.fields['password2'].required = False

# ユーザーログインフォーム（カスタム）
class UserLoginForm(AuthenticationForm):
    def get_user(self):
        return self.user_cache if self.user_cache and self.user_cache.is_authenticated else None
