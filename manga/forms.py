from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, PasswordResetForm
# Modelleri çağırıyoruz
from .models import Chapter, Profile, Comment

# 1. ÖZEL WIDGET (Panel İçin - Çoklu Resim Yükleme)
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class ChapterAdminForm(forms.ModelForm):
    bulk_images = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        label="Toplu Sayfa Yükleme (Resimleri Seç)",
        required=False,
        help_text="Bölüme ait tüm resimleri buraya sürükleyip bırakın veya seçin."
    )
    class Meta:
        model = Chapter
        fields = '__all__'

# 2. KULLANICI GÜNCELLEME (Ad, Soyad Kilidi Açıldı)
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label="E-posta", widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'E-posta adresiniz'}))
    
    # Ad ve Soyad alanlarını 'widget' ile yazılabilir hale getiriyoruz
    first_name = forms.CharField(
        label="Ad",
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adınız'})
    )
    last_name = forms.CharField(
        label="Soyad",
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Soyadınız'})
    )
    username = forms.CharField(label="Kullanıcı Adı", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kullanıcı Adı'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

# 3. PROFİL GÜNCELLEME (Instagram ve Telefon Kaldırıldı)
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'bio'] # Sadece Avatar ve Biyo kaldı
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Form elemanlarına bootstrap class ekle
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # Avatar ve Biyo için özel ayarlar
        self.fields['avatar'].widget.attrs.update({'class': 'form-control bg-dark text-white'})
        self.fields['bio'].widget.attrs.update({'rows': 3, 'placeholder': 'Kendinden bahset...'})

# 4. ÖZEL KAYIT FORMU (Türkçe ve Bootstrap'li)
# forms.py içindeki ilgili sınıfı güncelle:

class CustomUserCreationForm(UserCreationForm):
    # Alanları ZORUNLU (required=True) olarak tanımlıyoruz
    email = forms.EmailField(
        label="E-posta Adresi",
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'E-posta Adresi'})
    )
    first_name = forms.CharField(
        label="Ad",
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ad'})
    )
    last_name = forms.CharField(
        label="Soyad",
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Soyad'})
    )

    class Meta:
        model = User
        # Sıralama önemli:
        fields = ("username", "email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Kullanıcı Adı"
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Kullanıcı Adı'})
        # Yardım metinlerini temizleyelim, tasarım bozulmasın
        for field in self.fields:
            self.fields[field].help_text = None

# 5. ÖZEL ŞİFRE DEĞİŞTİRME FORMU
class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = "Mevcut Şifreniz"
        self.fields['new_password1'].label = "Yeni Şifre"
        self.fields['new_password2'].label = "Yeni Şifre (Tekrar)"
        
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_new_password1(self):
        old = self.cleaned_data.get('old_password')
        new = self.cleaned_data.get('new_password1')
        if old and new and old == new:
            raise forms.ValidationError("Yeni şifreniz, eski şifrenizle aynı olamaz!")
        return new

# 6. YORUM FORMU
class CommentForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Düşüncelerini paylaş...'}),
        label=""
    )
    class Meta:
        model = Comment
        fields = ['content', 'is_spoiler']

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Dedektif iş başında: Bu mail veritabanında var mı?
        if not User.objects.filter(email=email).exists():
            # Yoksa hata fırlat!
            raise forms.ValidationError("Bu e-posta adresiyle kayıtlı bir hesap bulunamadı!")
        return email