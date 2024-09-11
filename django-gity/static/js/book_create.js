const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const BarCode = urlParams.get('barcode');
const QrCode = urlParams.get('qrcode');

/* 
関数: fetchBookInfo
    サーバーから書籍情報を取得し、ページに表示する関数
引数:
    なし
戻り値:
    なし
*/
function fetchBookInfo() {
    // リクエストデータを作成
    const requestData = {
        barcode: BarCode, // バーコード
        qrcode: QrCode // QRコード
    };

    // Fetch APIを使用してサーバーにリクエストを送信
    fetch('book_create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData) // リクエストデータをJSON形式に変換して送信
    })
    .then(response => {
        // レスポンスのJSONデータを解析
        return response.json();
    })
    .then(data => {
        // 書籍情報を取得して表示
        console.log(data);
        // ここで書籍情報を取得して、適切な処理を行う
        if (data) {
            // ページ上に書籍情報を表示するための処理を追加
            const bookInfoDiv = document.createElement('div');
            bookInfoDiv.innerHTML = `
                <img src="${data.image_link}" alt="書籍画像">
            `;
            const targetElement = document.getElementById('targetElementId'); // 挿入する場所の要素を取得する
            targetElement.appendChild(bookInfoDiv);

            // フォームに書籍情報を自動入力
            var bookNameInput = document.getElementById('id_book_name');
            var authorNameInput = document.getElementById('id_author_name');
            var descriptionInput = document.getElementById('id_description');
            var imageLinkInput = document.getElementById('id_image_link');
            var barCodeInput = document.getElementById('id_bar_code');

            bookNameInput.value = data.book_name;
            authorNameInput.value = data.author_name;
            descriptionInput.value = data.description;
            imageLinkInput.value = data.image_link;
            barCodeInput.value = data.bar_code;
        }
    })
    .catch(error => {
        // エラーハンドリング
        console.error('Error fetching book information:', error);
    });
}

// fetchBookInfo関数を呼び出して書籍情報を取得
fetchBookInfo();