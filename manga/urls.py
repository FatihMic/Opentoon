from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .forms import CustomPasswordChangeForm 

urlpatterns = [
    # --- ANA SAYFA & LİSTELEME ---
    path('', views.ana_sayfa, name='home'),
    path('seri-listesi/', views.seri_listesi, name='seri_listesi'),
    path('tum-seriler/', views.tum_seriler, name='tum_seriler'),
    
    # FAZ 1: YENİ SAYFALAR
    path('siralama/', views.seri_siralamasi, name='seri_siralamasi'),

    # --- MANGA DETAY & OKUMA ---
    path('manga/<slug:slug>/', views.manga_detay, name='manga_detay'),
    # Okuma linkini 'oku/' olarak değiştirdim, 'manga/' ile karışmasın diye
    path('oku/<slug:slug>/<str:bolum_no>/', views.manga_oku, name='manga_oku'),
    path('indir/bolum/<int:chapter_id>/', views.manga_bolum_indir, name='manga_bolum_indir'),
    
    # --- KULLANICI İŞLEMLERİ ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.kayit_ol, name='register'),
    path('profile/', views.profil, name='profil'),

    # --- ŞİFRE İŞLEMLERİ ---
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='password_change.html',
        form_class=CustomPasswordChangeForm
    ), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html'), name='password_change_done'),

    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_action_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_action_done.html'), name='password_reset_complete'),

    # --- YAYINCI PANELİ ---
    path('panel/', views.yayinci_paneli, name='yayinci_paneli'),
    path('panel/hizli-seri-ekle/', views.hizli_seri_ekle, name='hizli_seri_ekle'),
    path('panel/hizli-grup-ekle/', views.hizli_grup_ekle, name='hizli_grup_ekle'),
    path('api/yayinci/bolum-yonetimi/', views.yayinci_bolum_sayfa_yonetimi, name='yayinci_bolum_yonetimi'),
    
    # --- YENİ EKLENEN DÜZENLEME API'LERİ (ÖNEMLİ) ---
    path('api/seri-getir/<int:id>/', views.seri_getir, name='seri_getir'),
    path('api/seri-duzenle/', views.seri_duzenle, name='seri_duzenle'),

    # --- ETKİLEŞİM & API ---
    path('api/search/', views.api_search, name='api_search'),
    path('like/<slug:slug>/', views.seri_begen, name='seri_begen'),
    path('rate/<slug:slug>/', views.puan_ver, name='puan_ver'),  # <-- DÜZELTİLEN SATIR (Eskisi: api/puan-ver...)
    path('api/save-progress/', views.ilerleme_kaydet, name='ilerleme_kaydet'),
    
    # GERİ BİLDİRİM API LİNKİ
    path('api/feedback/', views.feedback_al, name='feedback_al'),

    # BİLDİRİM API LİNKLERİ
    path('api/notifications/', views.bildirimleri_getir, name='bildirimleri_getir'),
    path('api/notifications/mark-read/', views.bildirimleri_okundu_isaretle, name='bildirimleri_okundu_isaretle'),

    # Yorum İşlemleri
    path('api/comment/like/<int:comment_id>/', views.yorum_begen, name='yorum_begen'),
    path('api/comment/delete/<int:comment_id>/', views.yorum_sil, name='yorum_sil'),
    
]