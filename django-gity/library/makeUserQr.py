import pyqrcode
import datetime
import PIL
import os
import base64
import numpy as np
from io import BytesIO
from django.conf import settings
from django.core.files import File

"""
関数: make_qr
    ユーザーのためにQRコードを生成し、画像として保存します
引数:
    user: ユーザーオブジェクト（メールアドレスとQRコードを保存するImageFieldを含む）
戻り値:
    なし
"""
def make_qr(user):
    # 現在の日時を取得
    dt_now = datetime.datetime.now()
    user_email = user.email
    username = user_email.split('@')[0]
    # ユーザー名とタイムスタンプを組み合わせた一意の名前を生成
    timestamp = 'user' + username + str(dt_now.microsecond).zfill(6)
    
    png_name = timestamp + '.png'
    # デバッグ用
    # print(png_name)
    
    # QRコードを作成
    qr_content = timestamp
    qrcode = pyqrcode.create(qr_content, error='H', version=4)
    qrcode_image = qrcode.png_as_base64_str(scale=10)
    
    # PIL形式の画像に変換
    qr_image = PIL.Image.open(BytesIO(base64.b64decode(qrcode_image)))
    
    # QRコードの特定の範囲を白く塗りつぶす
    qr_image_np = np.array(qr_image)             # PIL画像をNumPy配列に変換
    qr_image_np[150:260, 150:260] = 255          # QRコードの特定の範囲を白に変更
    qr_image = PIL.Image.fromarray(qr_image_np)  # NumPy配列をPIL画像に変換
    
    # 中央に挿入する別の画像を読み込み
    overlay_image = PIL.Image.open("static/image/gity.png")
    # overlay_imageをqr_imageに貼り付ける（必要に応じてサイズや位置を調整）
    overlay_image = overlay_image.resize((110, 110))          # サイズを調整
    qr_image.paste(overlay_image, (150, 150), overlay_image)  # 中央に貼り付け

    # 画像を保存するディレクトリが存在しない場合は作成
    save_directory = os.path.join(settings.BASE_DIR, 'static', 'image')
    print(save_directory)
    os.makedirs(save_directory, exist_ok=True)
    
    # 画像を保存
    qr_image.save(os.path.join(save_directory, png_name))
    
    # 保存したQRコードの画像ファイルをImageFieldに関連付けて保存
    with open(os.path.join(save_directory, png_name), 'rb') as f:
        user.QRcode.save(png_name, File(f), save=True)
        
    # 保存したファイルを削除
    file_path = os.path.join(save_directory, png_name)
    if os.path.exists(file_path):
        os.remove(file_path)