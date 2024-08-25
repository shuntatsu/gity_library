import qrcode
import random
import io

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from datetime import datetime

QR_CODES_PER_PAGE = 48  # 1ページあたりのQRコードの数

"""
関数: generate_qr_code_pdf
    指定された数のQRコードを生成し、A4サイズのPDFに配置する関数。
引数:
    buffer: PDFデータを保存するためのバッファ。
    num_qr: 生成するQRコードの数。
戻り値:
    なし（PDFはバッファに保存される）。
"""
def generate_qr_code_pdf(buffer, num_qr):
    # PDFの作成
    pdf_file = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # A4用紙に枠とQRコードを配置
    frame_size = 30 * mm
    qr_size = 28 * mm
    x_offset = (width - frame_size * 6) / 2
    y_offset = (height - frame_size * 8) / 2

    qr_count = 0
    used_codes = set()

    while qr_count < num_qr:
        for i in range(8):
            for j in range(6):
                if qr_count >= num_qr:
                    break

                # 枠の描画
                pdf_file.rect(x_offset, y_offset, frame_size, frame_size)

                # 重複しないQRコードのデータを生成
                while True:
                    today = datetime.now()
                    month_day = today.strftime("%m%d")
                    year = today.strftime("%Y")
                    data = f"book{random.randint(1000, 9999)}{month_day}{random.randint(1000, 9999)}{year}"
                    if data not in used_codes:
                        used_codes.add(data)
                        break

                # QRコードの生成
                qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
                qr.add_data(data)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")

                # QRコードを枠内に配置
                qr_x_offset = x_offset + (frame_size - qr_size) / 2
                qr_y_offset = y_offset + (frame_size - qr_size) / 2
                pdf_file.drawInlineImage(qr_img, qr_x_offset, qr_y_offset, width=qr_size, height=qr_size)

                x_offset += frame_size
                qr_count += 1

            x_offset = (width - frame_size * 6) / 2
            y_offset += frame_size

        if qr_count % QR_CODES_PER_PAGE == 0 or qr_count >= num_qr:
            pdf_file.showPage()
            x_offset = (width - frame_size * 6) / 2
            y_offset = (height - frame_size * 8) / 2

    pdf_file.save()