from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver

# 1. KATEGORİ (Aksiyon, Dram, Isekai vb.)
class Category(models.Model):
    name = models.CharField(max_length=50, verbose_name="Kategori Adı")
    slug = models.SlugField(unique=True)
    
    def __str__(self): return self.name

# 2. GRUP (Çeviri Grubu)
class Group(models.Model):
    name = models.CharField(max_length=100, verbose_name="Grup Adı")
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='group_logos/', blank=True)
    description = models.TextField(blank=True)
    discord_link = models.URLField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self): return self.name

# 3. SERİ (Manga/Webtoon/Manhwa/Manhua) - GÜNCELLENDİ
class Series(models.Model):
    title = models.CharField(max_length=200, verbose_name="Seri Adı")
    slug = models.SlugField(unique=True)
    cover_image = models.ImageField(upload_to='covers/')
    description = models.TextField()
    author = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # GÖRÜNTÜLENME SAYAÇLARI
    views = models.PositiveIntegerField(default=0, verbose_name="Görüntülenme Sayısı")
    
    # Bu seriyi görüntüleyen kullanıcıların listesi (Hesap bazlı kontrol için)
    viewed_by = models.ManyToManyField(User, related_name='viewed_series', blank=True)

    # KATEGORİLER
    categories = models.ManyToManyField(Category, related_name='series', blank=True, verbose_name="Kategoriler")
    
    # BEĞENİLER
    likes = models.ManyToManyField(User, related_name='liked_series', blank=True)
    
    # TÜR SEÇENEKLERİ (4 ANA TÜR EKLENDİ)
    TYPE_CHOICES = (
        ('manga', 'Manga (Japon)'),
        ('webtoon', 'Webtoon (Dikey)'),
        ('manhwa', 'Manhwa (Kore)'),
        ('manhua', 'Manhua (Çin)'),
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='webtoon')

    STATUS_CHOICES = (
        ('devam', '🟢 Devam Ediyor'),
        ('tamamlandi', '🔴 Final Yaptı (Tamamlandı)'),
        ('ara', '⏸️ Ara Verildi (Sezon Finali)'),
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='devam', verbose_name="Seri Durumu")
    
    # YÜKLEYEN KİŞİ (Herkes kendi yüklediği seriyi görsün diye)
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_series', verbose_name="Yükleyen Kişi")
    # ----------------------------------------

    @property
    def is_new(self):
        from django.utils import timezone
        from datetime import timedelta
        return self.created_at >= timezone.now() - timedelta(days=14)

    @property
    def total_likes(self): return self.likes.count()

    @property
    def average_rating(self):
        avg = self.ratings.all().aggregate(Avg('score'))['score__avg']
        return round(avg, 1) if avg else 0

    def __str__(self): return self.title

# 4. PUANLAMA
class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    series = models.ForeignKey(Series, related_name='ratings', on_delete=models.CASCADE)
    score = models.IntegerField()
    class Meta: unique_together = ('user', 'series')

# 5. BÖLÜM
class Chapter(models.Model):
    series = models.ForeignKey(Series, related_name='chapters', on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    number = models.FloatField(verbose_name="Bölüm No")
    title = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta: ordering = ['-number']
    def __str__(self): return f"{self.series.title} - {self.number}"

# 6. SAYFA (Resimler)
class Page(models.Model):
    chapter = models.ForeignKey(Chapter, related_name='pages', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='manga_pages/')
    page_number = models.IntegerField()
    class Meta: ordering = ['page_number']

# 7. OKUMA GEÇMİŞİ
class ReadingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    series = models.ForeignKey(Series, on_delete=models.CASCADE)
    last_chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    page_number = models.IntegerField(default=1) 
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta: 
        unique_together = ('user', 'series')
        ordering = ['-updated_at']

# 8. PROFİL (Avatar ve Biyo) - GÜNCELLENDİ (Tel & Insta Eklendi)
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', blank=True, verbose_name="Profil Resmi")
    bio = models.TextField(max_length=500, blank=True, verbose_name="Hakkımda")
    
    # YENİ ALANLAR
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Telefon Numarası")
    instagram_handle = models.CharField(max_length=50, blank=True, null=True, verbose_name="Instagram Kullanıcı Adı")

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'name') and self.avatar.name:
            if 'default.png' in self.avatar.name:
                return f"https://ui-avatars.com/api/?name={self.user.username}&background=random&color=fff&size=150"
            return self.avatar.url
        return f"https://ui-avatars.com/api/?name={self.user.username}&background=random&color=fff&size=150"

    def __str__(self): return f'{self.user.username} Profili'

# Otomatik Profil Oluşturma Sinyalleri
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# 9. YORUMLAR (Cevaplama ve Beğeni özellikli)
class Comment(models.Model):
    series = models.ForeignKey(Series, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(verbose_name="Yorumunuz")
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    
    # Cevaplama özelliği (Self-referencing Foreign Key)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    is_spoiler = models.BooleanField(default=False, verbose_name="Spoiler İçeriyor")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.series.title}"
    
    @property
    def num_likes(self):
        return self.likes.count()

# 10. GERİ BİLDİRİM SİSTEMİ (Öneri/Şikayet/Hata) - GÜNCELLENDİ (Admin Cevabı)
class Feedback(models.Model):
    TUR_SECENEKLERI = (
        ('hata', '⚠️ Hata Bildirimi'),
        ('oneri', '💡 Öneri'),
        ('sikayet', '😡 Şikayet'),
        ('diger', '💬 Diğer'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True) # Üye değilse de gönderebilsin
    type = models.CharField(max_length=10, choices=TUR_SECENEKLERI, default='hata')
    page_url = models.CharField(max_length=200, blank=True) # Hangi sayfada sorun yaşadı?
    message = models.TextField(verbose_name="Mesajınız")
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False, verbose_name="Çözüldü mü?")
    
    # YENİ ALANLAR (Admin Cevap Sistemi)
    reply = models.TextField(blank=True, null=True, verbose_name="Admin Cevabı")
    replied_at = models.DateTimeField(blank=True, null=True, verbose_name="Cevaplanma Tarihi")

    def __str__(self):
        return f"{self.get_type_display()} - {self.created_at.strftime('%d.%m.%Y')}"

# 11. BİLDİRİMLER (NOTIFICATIONS)
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.message}"