# Eğer forms.py'yi 'manga' klasörüne açtıysan:
from manga.forms import CustomPasswordResetForm
# (Eğer başka klasördeyse oranın adını yaz: from klasör_adi.forms ...)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # 1. ADMIN PANELİ (Burası Ana Yönetim)
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    

    # 2. TÜM ÖZELLİKLER BURADAN GELİYOR
    # (Profil, Manga Oku, Puan Ver, Beğen, Panel, API... Hepsi 'manga.urls' içinde var)
    # Bu satır sayesinde diğer dosyadaki 30+ özelliği buraya dahil etmiş oluyoruz.
    path('', include('manga.urls')),

    path('reset_password/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
]

# Medya Dosyaları (Resimlerin görünmesi için şart)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)