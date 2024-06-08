# urls.py
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include
from .views import index, book_rental, book_return, camera_streaming, book_manage, book_create, book_delete, book_list, qr_reading, login_op, login_rp
from .views import BookList, BookDetail, login_view, user_manage, logout_view , user_history, camera_qr, choose, qr_registration, registration, want_book
from django.conf import settings  # 追加
from django.conf.urls.static import static  # 追加

urlpatterns = [
    path('', index, name='index'),
    #path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    #path('choose', choose, name='choose'),
    path('registration', registration, name='registration'),
    path('qr_registration', qr_registration, name='qr_registration'), 
    path('qr_reading', qr_reading, name='qr_reading'),   
    path('user_manage/<int:page_num>', user_manage, name="user_manage"),
    path('book_manage/<int:page_num>', book_manage, name="book_manage"),
    path('book_rental', book_rental, name='book_rental'),
    path('book_return', book_return, name='book_return'),
    path('camera_streaming', camera_streaming, name='camera_streaming'),
    path('camera_qr', camera_qr,name='camera_qr'),
    path('detail/<int:pk>',BookDetail.as_view(), name='book_detail'),
    path('book_create', book_create, name="book_create"),
    path('book_delete/<int:num>', book_delete, name="book_delete"),
    path('book_list/<int:page_num>', book_list, name='book_list'),
    path('user_history', user_history, name="user_history"),
    path('want_book', want_book, name="want_book"),
    path('login/', login_op, name="login"),
    path('login_rp', login_rp, name="login_rp"),
]
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
