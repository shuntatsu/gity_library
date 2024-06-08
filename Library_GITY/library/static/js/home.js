// ページが読み込まれたときに実行される関数
document.addEventListener('DOMContentLoaded', function() {
    // メニュートグルの動作
    var menuToggle = document.getElementById('menu-toggle');
    var menu = document.querySelector('.menu');

    menuToggle.addEventListener('change', function() {
        if (this.checked) {
            menu.style.display = 'block';
        } else {
            menu.style.display = 'none';
        }
    });

    // フォームの送信時の動作
    var contactForm = document.querySelector('.contact-form');
    contactForm.addEventListener('submit', function(event) {
        event.preventDefault();
        // フォームの送信処理を行う
        // ...
        alert('お問い合わせが送信されました。');
        contactForm.reset();
    });
});