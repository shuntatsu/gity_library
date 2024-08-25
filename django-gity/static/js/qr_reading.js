src="https://cdn.rawgit.com/cozmo/jsQR/master/dist/jsQR.js"

// URLのクエリパラメータからバーコードを取得
const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const BarCode = urlParams.get('barcode');

// ビデオ要素を作成
var video = document.createElement('video');
// キャンバス要素を取得
var canvasElement = document.getElementById('canvas');
var canvas = canvasElement.getContext('2d');
var isReadQR = false;
var lastScannedTime = 0;

// カメラにアクセスしてビデオストリームを取得
navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
    .then((stream) => {
        video.srcObject = stream;
        video.setAttribute('playsinline', true);
        video.play();
        requestAnimationFrame(tick);
    })
    .catch((error) => {
        console.error('Error accessing camera:', error);
    });

/* 
関数: tick
    ビデオフレームをキャンバスに描画し、QRコードを読み取る
引数:
    なし
戻り値:
    なし
*/
function tick() {
    if (!isReadQR && video.readyState === video.HAVE_ENOUGH_DATA) {
        // キャンバスのサイズをビデオのサイズに合わせる
        canvasElement.height = video.videoHeight;
        canvasElement.width = video.videoWidth;
        canvas.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);
        
        // キャンバスから画像データを取得
        var imageData = canvas.getImageData(0, 0, canvasElement.width, canvasElement.height);
        
        // QRコードを読み取る
        var code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'dontInvert',
        });
        
        if (code && code.data) {
            var qrCodeValue = code.data;
            isReadQR = true;
            var barcodeValue = BarCode; // URLから取得したバーコードの値を使用

            // サーバーにPOSTリクエストを送信
            var xhr = new XMLHttpRequest();
            var url = '/library/book_create?barcode=' + barcodeValue + '&qrcode=' + qrCodeValue; // POSTリクエストを送信するURL
            xhr.open('POST', url, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onreadystatechange = function () {
                if (xhr.readyState === XMLHttpRequest.DONE) {
                    if (xhr.status === 200) {
                        var redirectURL = url;
                        window.location.href = redirectURL; // リダイレクト
                    } else {
                        console.error('バーコードやQRコードが見つかりませんでした');
                    }
                }
            };
            var params = JSON.stringify({ barcode: barcodeValue, qrcode: qrCodeValue }); // リクエストパラメーターを設定
            xhr.send(params); // リクエストを送信
        } else {
            console.log('入力はQRコードではありません。');
        }
    }
    requestAnimationFrame(tick);
}