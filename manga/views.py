import json
import zipfile
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404, HttpResponse
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count, Avg, F, Max
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta

# Modeller ve Formlar
from .models import (
    Series, Chapter, Group, Page, ReadingHistory, 
    Rating, Profile, Comment, Category, Feedback, Notification
)
from .forms import (
    UserUpdateForm, ProfileUpdateForm, 
    CustomUserCreationForm, CommentForm
)

# --- GÜVENLİK ---
def is_yayinci(user):
    return user.is_superuser or user.groups.filter(name='Yayıncı').exists()

# 1. ANA SAYFA
def ana_sayfa(request):
    tum_kategoriler = Category.objects.all()
    populer = Series.objects.order_by('-views')[:1]
    en_cok_okunanlar = Series.objects.order_by('-views')[:6]
    yuksek_puan = Series.objects.annotate(avg_score=Avg('ratings__score')).order_by('-avg_score')[:6]
    
    bir_hafta_once = timezone.now() - timedelta(days=7)

    # YENİ ÇIKANLAR (Son 1 Haftada Eklenenler)
    yeniler = Series.objects.filter(created_at__gte=bir_hafta_once).annotate(chapter_count=Count('chapters')).order_by('-created_at')[:12]

    # FİNAL YAPAN SERİLER
    final_yapanlar = Series.objects.filter(status='tamamlandi').order_by('-created_at')[:6]

    # SON YÜKLENEN BÖLÜMLER (Son 1 haftada güncellenen, bölüm bazlı gruplanmış seriler)
    son_guncellenenler_qs = Series.objects.filter(chapters__uploaded_at__gte=bir_hafta_once)\
        .annotate(last_update=Max('chapters__uploaded_at'))\
        .order_by('-last_update').distinct()[:12]
        
    son_bolum_listesi = []
    for seri in son_guncellenenler_qs:
        son_guncel_bolumler = seri.chapters.all().order_by('-number')[:3]
        son_bolum_listesi.append({
            'seri': seri,
            'bolumler': son_guncel_bolumler
        })

    okuma_gecmisi = []
    if request.user.is_authenticated:
        okuma_gecmisi = ReadingHistory.objects.filter(user=request.user).select_related('series', 'last_chapter').order_by('-updated_at')[:4]

    context = {
        'okuma_gecmisi': okuma_gecmisi,
        'populer_seri': populer[0] if populer else None, 
        'en_cok_okunanlar': en_cok_okunanlar,
        'yuksek_puanli_seriler': yuksek_puan,
        'yeni_seriler': yeniler,
        'kategoriler': tum_kategoriler, 
        'final_yapanlar': final_yapanlar,
        'son_bolum_listesi': son_bolum_listesi,
    }
    return render(request, 'index.html', context)

# 2. SERİ LİSTESİ (KÜTÜPHANE)
def seri_listesi(request):
    tum_seriler = Series.objects.all().order_by('-created_at')

    context = {
        'tum_seriler': tum_seriler,
    }
    return render(request, 'seri_listesi.html', context)

# FAZ 1: SERİ SIRALAMASI SAYFASI
def seri_siralamasi(request):
    sirala = request.GET.get('sirala', 'views')  # varsayılan: görüntülenme
    
    if sirala == 'puan':
        seriler = Series.objects.annotate(avg_score=Avg('ratings__score')).order_by('-avg_score')[:50]
    elif sirala == 'begeni':
        seriler = Series.objects.annotate(begeni_sayisi=Count('likes')).order_by('-begeni_sayisi')[:50]
    else:  # views (varsayılan)
        seriler = Series.objects.order_by('-views')[:50]
    
    context = {
        'seriler': seriler,
        'secili_siralama': sirala,
    }
    return render(request, 'seri_siralamasi.html', context)


# 3. MANGA DETAY
def manga_detay(request, slug):
    seri = get_object_or_404(Series, slug=slug)
    
    # --- SAYAÇ ---
    if request.user.is_authenticated:
        zaten_gordu = seri.viewed_by.filter(id=request.user.id).exists()
        if not zaten_gordu:
            seri.viewed_by.add(request.user)
            Series.objects.filter(id=seri.id).update(views=F('views') + 1)
            seri.refresh_from_db()

    # Bölümleri çek
    bolumler = Chapter.objects.filter(series=seri).order_by('-number')
    
    # KİLİT VERİLER
    en_son_cikan_bolum = bolumler.first() # Final bölümü
    ilk_bolum = bolumler.last() # Başlangıç
    
    yorumlar = seri.comments.filter(parent=None).order_by('-created_at')
    comment_form = CommentForm()

    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            yorum = comment_form.save(commit=False)
            yorum.series = seri
            yorum.user = request.user
            parent_id = request.POST.get('parent_id')
            if parent_id:
                parent_comment = Comment.objects.get(id=parent_id)
                yorum.parent = parent_comment
            yorum.save()
            
            # CEVAP BİLDİRİMİ
            if parent_id and parent_comment.user != request.user:
                from .models import Notification
                Notification.objects.create(
                    user=parent_comment.user,
                    message=f"{request.user.username} yorumunuza yanıt verdi.",
                    link=f"/manga/{slug}/"
                )
                
            return redirect('manga_detay', slug=slug)

    # --- KULLANICI DURUMU ---
    kaldigi_bolum = None
    kaldigi_sayfa = 1
    user_rating = 0
    seri_bitti_mi = False 

    if request.user.is_authenticated:
        gecmis = ReadingHistory.objects.filter(user=request.user, series=seri).first()
        
        if gecmis:
            kaldigi_bolum = gecmis.last_chapter
            kaldigi_sayfa = gecmis.page_number
            
            # --- YENİ MANTIK (Sayfa Sayısını Kontrol Et) ---
            is_last_chapter = (en_son_cikan_bolum and kaldigi_bolum.id == en_son_cikan_bolum.id)
            
            if is_last_chapter:
                toplam_sayfa = kaldigi_bolum.pages.count()
                if toplam_sayfa > 1 and kaldigi_sayfa < toplam_sayfa:
                    seri_bitti_mi = False
                else:
                    seri_bitti_mi = True
            else:
                seri_bitti_mi = False

        puan = Rating.objects.filter(user=request.user, series=seri).first()
        if puan: user_rating = puan.score

    context = {
        'seri': seri, 
        'bolumler': bolumler,
        'kaldigi_bolum': kaldigi_bolum,
        'kaldigi_sayfa': kaldigi_sayfa, 
        'user_rating': user_rating,
        'yorumlar': yorumlar,
        'comment_form': comment_form,
        'seri_bitti_mi': seri_bitti_mi,
        'ilk_bolum': ilk_bolum
    }
    return render(request, 'manga_detay.html', context)

# 4. TÜM SERİLER (TAB DESTEKLİ)
def tum_seriler(request):
    seriler = Series.objects.all()
    kategoriler = Category.objects.all()

    # SEKME (TAB) PARAMETRESİ
    tab = request.GET.get('tab', 'tum')

    if tab == 'tamamlanan':
        # Tamamlanan Seriler sekmesi: sadece final yapmış seriler
        seriler = seriler.filter(status='tamamlandi')
    elif tab == 'az':
        # A-Z sekmesi: alfabetik sıralama (diğer filtreler hâlâ geçerli)
        pass  # Sıralama aşağıda yapılacak

    query = request.GET.get('q')
    if query: seriler = seriler.filter(title__icontains=query)

    tur = request.GET.get('tur')
    if tur and tur != 'hepsi': seriler = seriler.filter(type=tur)

    durum = request.GET.get('durum')
    if durum and durum != 'hepsi': seriler = seriler.filter(status=durum)

    secili_kategoriler = request.GET.getlist('kategori')
    if secili_kategoriler: seriler = seriler.filter(categories__slug__in=secili_kategoriler).distinct()

    # SIRALAMA
    if tab == 'az':
        # A-Z sekmesinde daima alfabetik sıralama
        seriler = seriler.order_by('title')
    else:
        sirala = request.GET.get('sirala')
        if sirala == 'populer': seriler = seriler.order_by('-views')
        elif sirala == 'puan': seriler = seriler.annotate(avg_rate=Avg('ratings__score')).order_by('-avg_rate')
        elif sirala == 'eski': seriler = seriler.order_by('created_at')
        else: seriler = seriler.order_by('-created_at')

    context = {
        'seriler': seriler, 'kategoriler': kategoriler, 'query': query,
        'secili_tur': tur, 'secili_durum': durum,
        'secili_sirala': request.GET.get('sirala'),
        'secili_kategoriler': secili_kategoriler,
        'aktif_tab': tab,
    }
    return render(request, 'tum_seriler.html', context)

# 5. OKUMA EKRANI
def manga_oku(request, slug, bolum_no):
    seri = get_object_or_404(Series, slug=slug)
    temiz_no = str(bolum_no).lower().replace('bolum-', '').replace('bölüm-', '').replace(',', '.')
    
    try: 
        current_number = float(temiz_no)
    except ValueError: 
        raise Http404("Geçersiz bölüm numarası")

    bolum = get_object_or_404(Chapter, series=seri, number=current_number)
    resimler = bolum.pages.all().order_by('page_number')
    
    gelen_sayfa = int(request.GET.get('page', 1))
    baslangic_sayfasi = gelen_sayfa - 1 
    okuma_modu = request.GET.get('mode', 'default')

    sonraki = Chapter.objects.filter(series=seri, number__gt=current_number).order_by('number').first()
    onceki = Chapter.objects.filter(series=seri, number__lt=current_number).order_by('-number').first()

    if request.user.is_authenticated:
        ReadingHistory.objects.update_or_create(
            user=request.user, 
            series=seri,
            defaults={
                'last_chapter': bolum, 
                'page_number': gelen_sayfa
            }
        )

    context = {
        'seri': seri, 'bolum': bolum, 'resimler': resimler,
        'sonraki_bolum': sonraki, 'onceki_bolum': onceki,
        'start_index': baslangic_sayfasi, 'secili_mod': okuma_modu
    }
    return render(request, 'manga_oku.html', context)

# --- İNDİRME İŞLEMİ (ZIP) ---
def manga_bolum_indir(request, chapter_id):
    bolum = get_object_or_404(Chapter, id=chapter_id)
    
    # Bellekte bir ZIP dosyası oluştur
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for page in bolum.pages.all().order_by('page_number'):
            if page.image:
                try:
                    # Dosyanın adını sayfa numarasına göre belirliyoruz (örneğin 001.jpg)
                    uzanti = page.image.name.split('.')[-1]
                    dosya_adi = f"{int(page.page_number):03d}.{uzanti}"
                    zip_file.writestr(dosya_adi, page.image.read())
                except Exception as e:
                    print(f"Resim okunurken hata: {e}")
                    pass
    
    # ZIP dosyasını başa sar ve HTTP yanıtı olarak döndür
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/zip')
    
    # Dosya adını hazırlıyoruz: "seri-adi-bolum-1.zip"
    dosya_ism = f"{slugify(bolum.series.title)}-bolum-{bolum.number}.zip"
    response['Content-Disposition'] = f'attachment; filename="{dosya_ism}"'
    
    return response

# --- API İŞLEMLERİ ---

@login_required
def ilerleme_kaydet(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            series_slug = data.get('series_slug')
            chapter_id = data.get('chapter_id')
            page_num = data.get('page_num')
            
            seri = Series.objects.get(slug=series_slug)
            bolum = Chapter.objects.get(id=chapter_id)
            
            ReadingHistory.objects.update_or_create(
                user=request.user, series=seri,
                defaults={'last_chapter': bolum, 'page_number': page_num}
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})

@login_required
def yorum_begen(request, comment_id):
    if request.method == 'POST':
        try:
            yorum = Comment.objects.get(id=comment_id)
            if request.user in yorum.likes.all():
                yorum.likes.remove(request.user)
                liked = False
            else:
                yorum.likes.add(request.user)
                liked = True
                
                # BEĞENİ BİLDİRİMİ
                if yorum.user != request.user:
                    from .models import Notification
                    Notification.objects.create(
                        user=yorum.user,
                        message=f"{request.user.username} yorumunuzu beğendi.",
                        link=f"/manga/{yorum.series.slug}/"
                    )
            return JsonResponse({'liked': liked, 'count': yorum.likes.count()})
        except Comment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Yorum bulunamadı'})
    return JsonResponse({'status': 'error'})

@login_required
def yorum_sil(request, comment_id):
    if request.method == 'POST':
        try:
            yorum = Comment.objects.get(id=comment_id)
            if request.user == yorum.user or request.user.is_superuser:
                yorum.delete()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Yetkisiz işlem!'})
        except Comment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Yorum bulunamadı'})
    return JsonResponse({'status': 'error'})

@login_required
def puan_ver(request, slug):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            score = int(data.get('score'))
            if 1 <= score <= 5:
                seri = get_object_or_404(Series, slug=slug)
                Rating.objects.update_or_create(
                    user=request.user, series=seri, defaults={'score': score}
                )
                return JsonResponse({'status': 'success', 'new_avg': seri.average_rating})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})

@login_required
def seri_begen(request, slug):
    if request.method == 'POST':
        seri = get_object_or_404(Series, slug=slug)
        user = request.user
        if user in seri.likes.all():
            seri.likes.remove(user)
            liked = False
        else:
            seri.likes.add(user)
            liked = True
        return JsonResponse({'liked': liked, 'count': seri.likes.count()})
    return JsonResponse({'status': 'error'})

def api_search(request):
    query = request.GET.get('q', '')
    if len(query) > 1:
        results = Series.objects.filter(title__icontains=query)[:5]
        data = [{'title': s.title, 'slug': s.slug, 'cover': s.cover_image.url if s.cover_image else ''} for s in results]
        return JsonResponse({'results': data})
    return JsonResponse({'results': []})


@login_required
def profil(request):
    Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('profil')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    tum_gecmis = ReadingHistory.objects.filter(user=request.user).select_related('series', 'last_chapter').order_by('-updated_at')
    okuma_gecmisi = [] 

    for kayit in tum_gecmis:
        son_bolum = Chapter.objects.filter(series=kayit.series).order_by('-number').first()
        bitti_mi = False
        if son_bolum and kayit.last_chapter.id == son_bolum.id:
            toplam_sayfa = kayit.last_chapter.pages.count()
            if kayit.page_number >= toplam_sayfa:
                bitti_mi = True 
        
        if not bitti_mi:
            okuma_gecmisi.append(kayit)

    begendikleri = request.user.liked_series.all()
    bildirimler = Feedback.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'u_form': u_form, 
        'p_form': p_form, 
        'okuma_gecmisi': okuma_gecmisi,
        'begendikleri': begendikleri,
        'bildirimler': bildirimler
    }
    return render(request, 'profile.html', context)

def kayit_ol(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid(): 
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})


@login_required(login_url='login')
@user_passes_test(is_yayinci)
def yayinci_paneli(request):
    if request.method == 'POST':
        try:
            seri_id = request.POST.get('series')
            grup_id = request.POST.get('group')
            bolum_no = request.POST.get('number')
            baslik = request.POST.get('title')
            resimler = request.FILES.getlist('file')
            
            if not resimler:
                return JsonResponse({'status': 'error', 'message': 'Resim yok!'}, status=400)
            
            seri = Series.objects.get(id=seri_id)
            if not request.user.is_superuser and seri.uploader != request.user:
                return JsonResponse({'status': 'error', 'message': 'Bu seri size ait değil!'}, status=403)
            
            grup = Group.objects.get(id=grup_id)
            if not request.user.is_superuser and grup.owner != request.user:
                return JsonResponse({'status': 'error', 'message': 'Bu grup size ait değil!'}, status=403)
            
            yeni_bolum, created = Chapter.objects.get_or_create(
                series=seri, 
                number=bolum_no, 
                defaults={'group': grup, 'title': baslik}
            )
            
            if not created:
                yeni_bolum.group = grup
                yeni_bolum.title = baslik
                yeni_bolum.save()
            else:
                for u in seri.likes.all():
                    Notification.objects.create(
                        user=u,
                        message=f"{seri.title} serisinin {bolum_no}. bölümü eklendi!",
                        link=f"/oku/{seri.slug}/{bolum_no}/"
                    )
            
            mevcut = Page.objects.filter(chapter=yeni_bolum).count()
            for i, resim in enumerate(resimler):
                Page.objects.create(
                    chapter=yeni_bolum, 
                    image=resim, 
                    page_number=mevcut + i + 1
                )
            
            return JsonResponse({'status': 'success', 'message': 'Yüklendi'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    if request.user.is_superuser:
        seriler = Series.objects.all().order_by('-created_at')
        gruplar = Group.objects.all()
    else:
        seriler = Series.objects.filter(uploader=request.user).order_by('-created_at')
        gruplar = Group.objects.filter(owner=request.user)

    context = {
        'seriler': seriler,
        'gruplar': gruplar,
        'kategoriler': Category.objects.all()
    }
    return render(request, 'yayinci_paneli.html', context)

@login_required
@user_passes_test(is_yayinci)
def yayinci_bolum_sayfa_yonetimi(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            # 1. BÖLÜMLERİ GETİR
            if action == 'get_chapters':
                seri_id = request.POST.get('series_id')
                seri = Series.objects.get(id=seri_id)
                if not request.user.is_superuser and seri.uploader != request.user: return JsonResponse({'status': 'error', 'message': 'Yetkiniz yok!'})
                bolumler = Chapter.objects.filter(series_id=seri_id).order_by('-number')
                data = [{'id': b.id, 'number': b.number, 'title': b.title, 'page_count': b.pages.count()} for b in bolumler]
                return JsonResponse({'status': 'success', 'bolumler': data})
                
            # 2. BÖLÜM SİL
            elif action == 'delete_chapter':
                bolum_id = request.POST.get('chapter_id')
                bolum = Chapter.objects.get(id=bolum_id)
                if not request.user.is_superuser and bolum.series.uploader != request.user: return JsonResponse({'status': 'error', 'message': 'Yetkiniz yok!'})
                bolum.delete()
                return JsonResponse({'status': 'success'})
                
            # 3. SAYFALARI GETİR
            elif action == 'get_pages':
                bolum_id = request.POST.get('chapter_id')
                sayfalar = Page.objects.filter(chapter_id=bolum_id).order_by('page_number')
                data = [{'id': s.id, 'num': s.page_number, 'url': s.image.url} for s in sayfalar]
                return JsonResponse({'status': 'success', 'sayfalar': data})
                
            # 4. SAYFA SİL (Kalanları otomatik kaydırır)
            elif action == 'delete_page':
                sayfa_id = request.POST.get('page_id')
                sayfa = Page.objects.get(id=sayfa_id)
                bolum = sayfa.chapter
                sayfa.delete()
                # Arada boşluk kalmasın diye sayfaları yeniden numaralandır
                for i, s in enumerate(bolum.pages.all().order_by('page_number')):
                    s.page_number = i + 1
                    s.save()
                return JsonResponse({'status': 'success'})
                
            # 5. EKSİK SAYFA EKLE
            elif action == 'add_pages':
                bolum_id = request.POST.get('chapter_id')
                bolum = Chapter.objects.get(id=bolum_id)
                resimler = request.FILES.getlist('files')
                mevcut = bolum.pages.count()
                for i, res in enumerate(resimler):
                    Page.objects.create(chapter=bolum, image=res, page_number=mevcut + i + 1)
                return JsonResponse({'status': 'success'})
                
            # 6. SERİ SİL
            elif action == 'delete_series':
                seri_id = request.POST.get('series_id')
                seri = Series.objects.get(id=seri_id)
                if not request.user.is_superuser and seri.uploader != request.user: return JsonResponse({'status': 'error', 'message': 'Yetkiniz yok!'})
                seri.delete()
                return JsonResponse({'status': 'success'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Geçersiz istek'})

@login_required
@user_passes_test(is_yayinci)
def hizli_seri_ekle(request):
    if request.method == 'POST':
        try:
            isim = request.POST.get('title')
            tur = request.POST.get('type')
            durum = request.POST.get('status', 'devam') # EKLENDİ
            yazar = request.POST.get('author')
            aciklama = request.POST.get('description')
            kapak = request.FILES.get('cover_image')
            secilen_kategoriler = request.POST.getlist('categories')

            base_slug = slugify(isim)
            slug = base_slug
            counter = 1
            while Series.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            yeni = Series.objects.create(
                title=isim, 
                slug=slug, 
                type=tur, 
                status=durum, # EKLENDİ
                author=yazar, 
                description=aciklama, 
                cover_image=kapak,
                uploader=request.user
            )
            
            if secilen_kategoriler:
                yeni.categories.set(secilen_kategoriler)

            return JsonResponse({'status': 'success', 'id': yeni.id, 'title': yeni.title})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})

@login_required
@user_passes_test(is_yayinci)
def hizli_grup_ekle(request):
    if request.method == 'POST':
        try:
            isim = request.POST.get('name')
            yeni = Group.objects.create(name=isim, slug=slugify(isim), owner=request.user)
            return JsonResponse({'status': 'success', 'id': yeni.id, 'name': yeni.name})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})

@login_required
@user_passes_test(is_yayinci)
def seri_getir(request, id):
    try:
        seri = Series.objects.get(id=id)
        kategori_ids = list(seri.categories.values_list('id', flat=True))
        data = {
            'id': seri.id,
            'title': seri.title,
            'type': seri.type,
            'status': seri.status, # EKLENDİ
            'author': seri.author,
            'description': seri.description,
            'categories': kategori_ids,
            'cover_url': seri.cover_image.url if seri.cover_image else None
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Series.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Seri bulunamadı'})

@login_required
@user_passes_test(is_yayinci)
def seri_duzenle(request):
    if request.method == 'POST':
        try:
            seri_id = request.POST.get('series_id')
            seri = Series.objects.get(id=seri_id)
            if not request.user.is_superuser and seri.uploader != request.user: return JsonResponse({'status': 'error', 'message': 'Yetkiniz yok!'})
            
            seri.title = request.POST.get('title')
            seri.type = request.POST.get('type')
            seri.status = request.POST.get('status', 'devam') # EKLENDİ
            seri.author = request.POST.get('author')
            seri.description = request.POST.get('description')
            
            if request.FILES.get('cover_image'):
                seri.cover_image = request.FILES.get('cover_image')

            seri.save()
            seri.categories.set(request.POST.getlist('categories'))
            
            return JsonResponse({'status': 'success', 'message': 'Seri güncellendi!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})

def feedback_al(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            Feedback.objects.create(
                user=request.user if request.user.is_authenticated else None,
                type=data.get('type'),
                message=data.get('message'),
                page_url=data.get('url')
            )
            return JsonResponse({'status': 'success', 'message': 'Bildiriminiz ulaştı!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})

@login_required
def bildirimleri_getir(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    data = [{
        'id': n.id,
        'message': n.message,
        'link': n.link,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime("%d.%m %H:%M")
    } for n in notifications]
    return JsonResponse({'status': 'success', 'notifications': data, 'unread_count': unread_count})

@login_required
def bildirimleri_okundu_isaretle(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})