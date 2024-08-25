from django.contrib.auth.backends import BaseBackend
from .models import CustomUser, QRCode
from .makeUserQr import make_qr

"""
関数: authenticate
    QRコードを使用してユーザーを認証します。
引数:
    request: HTTPリクエストオブジェクト
    qr_data: 認証に使用するQRコードデータ
戻り値:
    認証されたユーザーオブジェクト、または認証に失敗した場合はNone
"""
class QRCodeBackend(BaseBackend):
    def authenticate(self, request, qr_data=None):
        try:
            # QRコードデータに基づいてユーザーを取得
            qrcode = QRCode.objects.get(url=qr_data)
            user = qrcode.user
            return user
        except QRCode.DoesNotExist:
            return None

    """
    関数: get_user
        ユーザーIDに基づいてユーザーを取得します。
    引数:
        user_id: ユーザーID
    戻り値:
        ユーザーオブジェクト、またはユーザーが存在しない場合はNone
    """
    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None


"""
関数: authenticate
    OIDCクライアントを使用してユーザーを認証します。
引数:
    request: HTTPリクエストオブジェクト
    client: AuthlibのOAuthクライアント
戻り値:
    認証されたユーザーオブジェクト、または認証に失敗した場合はNone
"""
class OidcBackend(BaseBackend):
    def authenticate(self, request, client=None):
        if client is None:
            return None

        # トークンリクエスト
        token = client.authorize_access_token(request)
        print("token:", token)

        # IDトークンに基づいてDjangoユーザーを作成
        if token and 'userinfo' in token:
            assert 'email' in token['userinfo']
            email = token['userinfo']['email']  # メールアドレスを取得する
            try:
                # メールアドレスでユーザーを検索する
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                # ユーザーが存在しない場合は新しいユーザーを作成する
                user = CustomUser(email=email)
                user.is_staff = False
                user.is_superuser = False

                user.save()
                make_qr(user)
            return user

        return None

    """ 
    関数: get_user
        ユーザーIDに基づいてユーザーを取得します。
    引数:
        user_id: ユーザーID
    戻り値:
        ユーザーオブジェクト、またはユーザーが存在しない場合はNone
    """
    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None