src="https://serratus.github.io/quaggaJS/examples/js/quagga.min.js"

document.addEventListener('DOMContentLoaded', function () {
    var video = document.createElement('video');
    var canvas = document.querySelector('#canvas');
    var resultText = document.querySelector('#result');
    var isDetecting = false;

    // カメラの映像を取得
    navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment'
            },
            audio: false
        })
        .then(function (stream) {
            video.srcObject = stream;
            video.play();

            // ビデオの読み込みとサイズの設定が終わった後にanimate関数を呼び出す
            video.addEventListener('loadedmetadata', function () {
                /* 
                関数: animate
                    ビデオフレームをキャンバスに描画し、バーコードを検出する
                引数:
                    なし
                戻り値:
                    なし
                */
                function animate() {
                    // キャンバスのサイズをビデオのサイズに合わせる
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    var ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0, video.videoWidth, video.videoHeight, 0, 0, canvas.width, canvas.height);

                    // 検出領域のボックスを描画
                    var box = {
                        x: 50,
                        y: (canvas.height - 150) / 2,
                        w: canvas.width - 100,
                        h: 150
                    };

                    ctx.beginPath();
                    ctx.strokeStyle = 'red';
                    ctx.lineWidth = 2;
                    ctx.rect(box.x, box.y, box.w, box.h);
                    ctx.stroke();

                    // 検出領域の画像をバッファに描画
                    var buf = document.createElement('canvas');
                    buf.width = box.w;
                    buf.height = box.h;
                    buf.getContext('2d').drawImage(canvas, box.x, box.y, box.w, box.h, 0, 0, box.w, box.h);

                    // バーコード検出が行われていない場合に検出を開始
                    if (!isDetecting) {
                        isDetecting = true;
                        buf.toBlob(function (blob) {
                            var reader = new FileReader();
                            reader.readAsDataURL(blob);
                            reader.onload = function () {
                                Quagga.decodeSingle({
                                        decoder: {
                                            readers: ["ean_reader"],
                                        },
                                        src: reader.result
                                    },
                                    function (result) {
                                        if (result && result.codeResult) {
                                            var barcodeValue = result.codeResult.code;

                                            // バーコードを読み取ったらリダイレクトするURL
                                            var redirectURL = '/library/qr_reading?barcode=' + barcodeValue;

                                            // 結果を表示
                                            resultText.textContent = barcodeValue;

                                            // バーコードが読み取られたら指定のURLにリダイレクト
                                            window.location.href = redirectURL;
                                        }
                                        isDetecting = false;
                                    });
                            };
                        });
                    }
                    requestAnimationFrame(animate);
                }

                animate();
            });
        })
        .catch(function (e) {
            resultText.textContent = JSON.stringify(e);
        });
});