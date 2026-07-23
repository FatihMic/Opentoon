from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Series, Chapter, Group, Page, 
    Category, Comment, Profile, Feedback
)

# 1. KATEGORİ
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

# 2. GRUP
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')
    prepopulated_fields = {'slug': ('name',)}

# 3. SERİ
@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'author', 'created_at')
    list_filter = ('type', 'categories')
    search_fields = ('title', 'author')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('categories',)

# 4. SAYFALAR (Inline)
class PageInline(admin.TabularInline):
    model = Page
    extra = 0
    fields = ('image', 'page_number', 'image_preview')
    readonly_fields = ('image_preview',)

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('page_number')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; border-radius: 5px;" />', obj.image.url)
        return "Yok"
    image_preview.short_description = "Önizleme"

# 5. BÖLÜM
@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('series', 'number', 'title', 'group', 'uploaded_at')
    list_filter = ('series', 'group')
    search_fields = ('series__title', 'title')
    autocomplete_fields = ['series']
    inlines = [PageInline]

# 6. DİĞER STANDART MODELLER
admin.site.register(Comment)
admin.site.register(Profile)

# 7. GERİ BİLDİRİM (FEEDBACK) - HATA DÜZELTİLDİ
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('type_badge', 'user', 'short_message', 'is_resolved', 'created_at')
    list_filter = ('is_resolved', 'type', 'created_at')
    search_fields = ('message', 'user__username')
    list_editable = ('is_resolved',)
    
    # Detay sayfası alanları
    fields = ('user', 'type', 'page_url', 'message', 'created_at', 'reply', 'is_resolved')
    readonly_fields = ('user', 'type', 'page_url', 'message', 'created_at')

    # Atomik Kayıt İşlemi
    def save_model(self, request, obj, form, change):
        if obj.reply and not obj.replied_at:
            from django.utils import timezone
            obj.replied_at = timezone.now()
            obj.is_resolved = True 
        super().save_model(request, obj, form, change)

    # Renkli Rozet Fonksiyonu (list_display'deki hata buradaydı)
    def type_badge(self, obj):
        colors = {
            'hata': '#dc3545',    # Kırmızı
            'oneri': '#198754',   # Yeşil
            'sikayet': '#fd7e14', # Turuncu
            'diger': '#6c757d'    # Gri
        }
        color = colors.get(obj.type, '#000')
        return format_html(
            '<span style="color:white; background-color:{}; padding:3px 10px; border-radius:12px; font-weight:bold; font-size:11px;">{}</span>',
            color, obj.get_type_display()
        )
    type_badge.short_description = "Tür"

    # Mesaj Özeti Fonksiyonu (list_display'deki hata buradaydı)
    def short_message(self, obj):
        if obj.message and len(obj.message) > 50:
            return obj.message[:50] + "..."
        return obj.message
    short_message.short_description = "Mesaj Özeti"