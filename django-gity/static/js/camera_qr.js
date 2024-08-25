src="https://cdn.rawgit.com/cozmo/jsQR/master/dist/jsQR.js"

const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const userIdParam = urlParams.get('user_id');
const bookIdParam = urlParams.get('book_id');
const strParam = urlParams.get('str');

// オーバーレイにstrを表示
const overlay = document.getElementById('overlay');
overlay.innerText = strParam; // オーバーレイにstrを表示する

var video = document.createElement('video');
var canvasElement = document.getElementById('canvas');
var canvas = canvasElement.getContext('2d');
var isReadQR = false;
var username = "";
var lastScannedTime = 0; // 最後にQRコードをスキャンした時刻

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
    カメラ映像からQRコードを読み取り、適切な処理を行う関数
引数:
    なし
戻り値:
    なし
*/
function tick() {
    if (!isReadQR && video.readyState === video.HAVE_ENOUGH_DATA) {
        canvasElement.style.display = 'block';
        canvasElement.height = video.videoHeight;
        canvasElement.width = video.videoWidth;
        canvas.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);
        var imageData = canvas.getImageData(0, 0, canvasElement.width, canvasElement.height);
        var code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'dontInvert',
        });
        if (code && code.data) {
            var qrCodeValue = code.data;
            var currentTime = new Date().getTime();
            if (currentTime - lastScannedTime >= 1000) {
                lastScannedTime = currentTime;
                isReadQR = true;
                
                // URL形式であるかどうかを確認するための正規表現
                var urlRegex = /^(?:https?:\/\/)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z0-9]+(?:\/[^\/?#]+)?(?:\?[^#]+)?(?:#.*)?$/;

                /* 
                関数: getParameterValue
                    URLから指定されたパラメーターの値を取得する関数
                引数:
                    key: 取得したいパラメーターのキー
                    url: URL文字列
                戻り値:
                    パラメーターの値（存在しない場合は空文字）
                */
                function getParameterValue(key, url) {
                    // URLがURL形式でない場合は空文字を返す
                    if (!urlRegex.test(url)) {
                        return '';
                    }
                    // URLから?以降の部分を取得
                    var queryString = url.split('?')[1];
                    // クエリ文字列が存在しない場合は空文字を返す
                    if (!queryString) {
                        return '';
                    }
                    // クエリ文字列を&で分割して、キーと値のペアにする
                    var params = queryString.split('&');
                    // パラメーターのキーを検索して値を返す
                    for (var i = 0; i < params.length; i++) {
                        var pair = params[i].split('=');
                        if (pair[0] === key) {
                            // パーセントエンコードされた値をデコードして返す
                            return decodeURIComponent(pair[1]);
                        }
                    }
                    // キーが見つからない場合は空文字を返す
                    return '';
                }

                try {
                    if (urlRegex.test(qrCodeValue) !== '') {
                        // URLを解析
                        var url = new URL(qrCodeValue);

                        // パスを取得
                        var path = url.pathname;

                        // パスを / で分割して配列に格納
                        var parts = path.split('/');

                        // 最後の要素を取得
                        var username = parts.pop();

                        console.log("Username:", username);
                        qrCodeValue = username;
                    } else {
                        console.log('入力はURL形式ではありません。');
                    }
                } catch (error) {
                    // エラーが発生した場合はログに出力するなどの適切なエラー処理を行う
                    console.error('An error occurred while parsing the URL:', error);
                }
                
                // ユーザー認証
                if (username !== "" || qrCodeValue.substring(0, 4) === "user") {
                    if (!bookIdParam) {
                        var redirectURL = "/library/camera_qr?str=本のQRコードをかざしてください&user_id=" + qrCodeValue;
                        overlay.innerHTML = strParam;
                        overlay.style.display = 'block';
                        window.location.href = redirectURL;
                    } else {
                        var xhr = new XMLHttpRequest();
                        var url = '/library/book_rental' + '?user_id=' + qrCodeValue + '&book_id=' + encodeURIComponent(bookIdParam);
                        xhr.open('POST', url, true);
                        xhr.setRequestHeader('Content-Type', 'application/json');
                        xhr.onreadystatechange = function () {
                            if (xhr.readyState === XMLHttpRequest.DONE) {
                                if (xhr.status === 200) {
                                    var redirectURL = "/library/camera_qr?str=レンタルしました。返却期間は２週間です&user_id=" + qrCodeValue;
                                    overlay.innerHTML = strParam;
                                    overlay.style.display = 'block';
                                    window.location.href = redirectURL;
                                } else {
                                    console.error('Book rental request failed');
                                }
                            }
                        };
                        var params = JSON.stringify({ user_id: userIdParam, book_id: bookIdParam });
                        xhr.send(params);
                    }
                
                //　本認証
                } else if (qrCodeValue.substring(0, 4) === "book") {
                    if (!userIdParam) {
                        var xhr = new XMLHttpRequest();
                        var url = '/library/book_rental' + '?book_id=' + qrCodeValue;
                        xhr.open('POST', '/library/book_return/', true);
                        xhr.setRequestHeader('Content-Type', 'application/json');
                        xhr.onreadystatechange = function () {
                            if (xhr.readyState === XMLHttpRequest.DONE) {
                                if (xhr.status === 200) {
                                    var redirectURL = "/library/camera_qr?str=本を返却しました";
                                    overlay.innerHTML = strParam;
                                    overlay.style.display = 'block';
                                    window.location.href = redirectURL;
                                } else {
                                    var redirectURL = "/library/camera_qr?str=ユーザー認識QRをかざしてください&book_id=" + qrCodeValue;
                                    overlay.innerHTML = strParam;
                                    overlay.style.display = 'block';
                                    window.location.href = redirectURL;
                                }
                            }
                        };
                        xhr.send();
                    } else {
                        var xhr = new XMLHttpRequest();
                        var url = '/library/book_rental' + '?user_id=' + encodeURIComponent(userIdParam) + '&book_id=' + qrCodeValue;
                        xhr.open('POST', url, true);
                        xhr.setRequestHeader('Content-Type', 'application/json');
                        xhr.onreadystatechange = function () {
                            if (xhr.readyState === XMLHttpRequest.DONE) {
                                if (xhr.status === 200) {
                                    var redirectURL = "/library/camera_qr?str=レンタルしました。返却期間は２週間です&user_id=" + encodeURIComponent(userIdParam);
                                    overlay.innerHTML = strParam;
                                    overlay.style.display = 'block';
                                    window.location.href = redirectURL;
                                } else {
                                    console.error('Book rental request failed');
                                }
                            }
                        };
                        var params = JSON.stringify({ user_id: userIdParam, book_id: qrCodeValue });
                        xhr.send(params);
                    }
                } else {
                    var redirectURL = "/library/camera_qr?str=QRコードをかざしてください";
                    overlay.innerHTML = strParam;
                    overlay.style.display = 'block';
                    window.location.href = redirectURL;
                }
            }
        }
    }
    requestAnimationFrame(tick);
}

// 30秒後にリダイレクトする
setTimeout(function () {
    var redirectURL = "/library/camera_qr?str=QRコードをかざしてください";
    window.location.href = redirectURL;
}, 30000);