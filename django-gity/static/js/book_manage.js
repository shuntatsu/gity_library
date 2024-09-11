document.getElementById('qr-form').addEventListener('submit', function(event) {
    event.preventDefault(); // フォームのデフォルトの送信動作を防止

    var numQR = document.getElementById('num_qr').value; // フォームからQRコードの数を取得

    /* 
    関数: fetchBookInfo
        Djangoのビューにデータを送信し、PDFの生成をトリガーする関数
    引数:
        なし
    戻り値:
        なし
    */
    fetch('library/book_manage', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}' // CSRFトークンをヘッダーに追加
        },
        body: JSON.stringify({ num_qr: numQR }) // リクエストボディにQRコードの数をJSON形式で送信
    })
    .then(response => response.json()) // レスポンスをJSON形式に変換
    .then(data => {
        // PDFの生成が完了した後の処理
        console.log(data.message); // サーバーからのメッセージをコンソールに表示
    })
    .catch(error => {
        // エラーハンドリング
        console.error('Error:', error); // エラーをコンソールに表示
    });
});
