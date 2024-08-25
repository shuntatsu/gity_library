src="https://cdn.rawgit.com/cozmo/jsQR/master/dist/jsQR.js"

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

            // URLの正規表現
            var urlRegex = /^(?:https?:\/\/)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z0-9]+(?:\/[^\/?#]+)?(?:\?[^#]+)?(?:#.*)?$/;

            /* 
            関数: getParameterValue
                URLから指定されたパラメータの値を取得する
            引数:
                key: 取得したいパラメータのキー
                url: 検索対象のURL
            戻り値:
                パラメータの値（存在しない場合は空文字列）
            */
            function getParameterValue(key, url) {
                if (!urlRegex.test(url)) {
                    return '';
                }
                var queryString = url.split('?')[1];
                if (!queryString) {
                    return '';
                }
                var params = queryString.split('&');
                for (var i = 0; i < params.length; i++) {
                    var pair = params[i].split('=');
                    if (pair[0] === key) {
                        return decodeURIComponent(pair[1]);
                    }
                }
                return '';
            }

            try {
                if (urlRegex.test(qrCodeValue)) {
                    var url = new URL(qrCodeValue);
                    var path = url.pathname;
                    var parts = path.split('/');
                    var username = parts.pop();
                    var sitename = url.hostname;

                    // サーバーにPOSTリクエストを送信
                    var xhr = new XMLHttpRequest();
                    var url = '/library/qr_registration?user_id=' + username + '&sitename=' + sitename; // POSTリクエストを送信するURL
                    xhr.open('POST', url, true);
                    xhr.setRequestHeader('Content-Type', 'application/json');
                    xhr.onreadystatechange = function () {
                        if (xhr.readyState === XMLHttpRequest.DONE) {
                            if (xhr.status === 200) {
                                var redirectURL = "/library/registration";
                                window.location.href = redirectURL; // リダイレクト
                            } else {
                                console.error('登録できませんでした');
                            }
                        }
                    };
                    var params = JSON.stringify({ user_id: username, sitename: sitename }); // リクエストパラメーターを設定
                    xhr.send(params); // リクエストを送信
                } else {
                    console.log('入力はURL形式ではありません。');
                }
            } catch (error) {
                console.error('An error occurred while parsing the URL:', error);
            }
        }
    }
    requestAnimationFrame(tick);
}