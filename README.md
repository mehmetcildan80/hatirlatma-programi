# Hatırlatma Programı

Windows kullanıcıları için küçük, sağlam ve Türkçe bir masaüstü görev ve
hatırlatma uygulamasıdır. Görevleri tarihleriyle saklar ve belirlenen tek genel
saatte ertesi günün açık görevlerini özel bir uyarı penceresinde gösterir.

## Mevcut özellikler

- Görev ekleme, listeleme, düzenleme ve silme
- Görevleri tamamlandı veya açık olarak işaretleme
- Bugün, Yarın ve Tüm Görevler görünümleri
- SQLite üzerinde kalıcı yerel veri saklama
- Değiştirilebilir tek genel hatırlatma saati (varsayılan `15:00`)
- Ertesi günün açık görevleri için özel hatırlatma penceresi
- Açık kullanıcı onayı ve kalıcı 10 dakikalık erteleme
- Kaçırılmış hatırlatmayı sonraki başlangıçta gösterme
- Sistem tepsisinde arka planda çalışma
- Kullanıcıya özel Windows Startup kısayolu

## Gereksinimler

- Windows 10 veya Windows 11
- Python 3.10 veya üzeri
- PySide6 6.7 veya üzeri

## Kurulum ve çalıştırma

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Uygulamayı daha sonra çalıştırmak için:

```powershell
python app.py
```

## Yerel veri konumu

Görevler, ayarlar ve günlük hatırlatma kayıtları aşağıdaki kullanıcıya özel
konumda saklanır:

```text
%LOCALAPPDATA%\Hatirlatici\hatirlatici.db
```

Bu veritabanı proje klasöründe değildir ve Git'e eklenmez.

## Windows Startup davranışı

Ayarlar ekranındaki **Windows ile birlikte başlat** seçeneği yalnızca mevcut
kullanıcının aşağıdaki Startup klasöründe `Hatirlatici.lnk` oluşturur:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

Startup üzerinden çalıştırıldığında ana pencere açılmaz ve uygulama sistem
tepsisinde başlar. Zamanı geçmiş, onaylanmamış bir hatırlatma varsa uyarı
penceresi yine gösterilir. Yönetici yetkisi, Registry veya Task Scheduler
kullanılmaz.

## Testler

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py hatirlatici tests
```

Testler gerçek saati beklemez; hatırlatma senaryolarında denetlenebilir sahte
zaman kullanılır.

## Kullanım notu

Ana pencerenin kapatma düğmesi uygulamayı gizler. Uygulamayı tamamen kapatmak
için sistem tepsisi menüsündeki **Çıkış** seçilmelidir. Hatırlatma yalnızca
**Gördüm / Onayla** düğmesiyle onaylanır; pencereyi kapatmak onay sayılmaz.

## Henüz eklenmeyen özellikler

- EXE paketleme ve installer
- Otomatik güncelleme
- Ağ, bulut ve çok kullanıcılı çalışma
- Outlook veya Google entegrasyonu
- Excel ve yapay zekâ özellikleri
- Tema sistemi
- Görev başına ayrı veya birden fazla genel hatırlatma saati
