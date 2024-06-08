from django.contrib.auth.backends import BaseBackend
from .models import CustomUser, QRCode
import pyqrcode
import datetime
import PIL
from io import BytesIO
import base64
from django.core.files import File
from django.conf import settings
import os
import numpy as np

def make_qr(user):
    dt_now = datetime.datetime.now()
    user_email = user.email
    username = user_email.split('@')[0]
    timestamp = 'user' + username + str(dt_now.microsecond).zfill(6)
    
    png_name = timestamp + '.png'
    print(png_name)
    
    # QR コードを作成します
    qr_content = timestamp
    qrcode = pyqrcode.create(qr_content, error='H', version=4)
    qrcode_image = qrcode.png_as_base64_str(scale=10)
    # PIL形式の画像に変換します
    qr_image = PIL.Image.open(BytesIO(base64.b64decode(qrcode_image)))
    
    # QRコードの特定の範囲を白く塗りつぶします
    qr_image_np = np.array(qr_image)  # PIL画像をNumPy配列に変換
    qr_image_np[150:260, 150:260] = 255  # QRコードの特定の範囲を白に変更
    qr_image = PIL.Image.fromarray(qr_image_np)  # NumPy配列をPIL画像に変換
    
    # 中央に挿入する別の画像を読み込みます
    overlay_image = PIL.Image.open("library/static/image/gity.png")
    
    # 画像を保存するディレクトリが存在しない場合は作成します
    save_directory = os.path.join(settings.BASE_DIR, 'library', 'static', 'image')
    print(save_directory)
    os.makedirs(save_directory, exist_ok=True)
    
    # 画像を保存します
    qr_image.save(os.path.join(save_directory, png_name))
    
    # 保存したQRコードの画像ファイルをImageFieldに関連付けて保存します
    with open(os.path.join(save_directory, png_name), 'rb') as f:
        user.QRcode.save(png_name, File(f), save=True)
        
    file_path = os.path.join(save_directory, png_name)
    if os.path.exists(file_path):
        os.remove(file_path)
          
class QRCodeBackend(BaseBackend):
    def authenticate(self, request, qr_data=None):
        try:
            qrcode = QRCode.objects.get(url=qr_data)
            user = qrcode.user
            return user
        except QRCode.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
        
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User


class OidcBackend(BaseBackend):
    """
    custom backend for OIDC
    """
    def authenticate(self, request, client=None):
        """
        overriding method.
        params
            client: OAuth client of Authlib
        """
        if client is None:
            return None

        # token request
        token = client.authorize_access_token(request)
        print("token:",token)
        # makes django user according to ID token
        if token and 'userinfo' in token:
            assert 'email' in token['userinfo']
            email = token['userinfo']['email']  # メールアドレスを取得する
            try:
                user = CustomUser.objects.get(email=email)  # メールアドレスでユーザーを検索する
            except CustomUser.DoesNotExist:
                user = CustomUser(email=email)  # ユーザーが存在しない場合は新しいユーザーを作成する
                user.is_staff = False
                user.is_superuser = False

                user.save()
                make_qr(user)
            return user

                # some error handling
                # ...
            return None

    def get_user(self, user_id):
        """
        overriding method.
        """
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
        