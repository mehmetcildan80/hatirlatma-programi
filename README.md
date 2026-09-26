# Hatırlatma Programı

Windows kullanıcıları için küçük, sağlam ve Türkçe bir masaüstü görev ve
hatırlatma uygulamasıdır. Görevleri tarihleriyle saklar ve belirlenen tek genel
saatte ertesi günün açık görevlerini özel bir uyarı penceresinde gösterir.

## Mevcut özellikler

- Görev ekleme, listeleme, düzenleme ve silme
- Aynı tarih için çok sayıda görevi tek transaction ile toplu ekleme
- Görevleri tamamlandı veya açık olarak işaretleme
- Bugün, Yarın ve Tüm Görevler görünümleri
- SQLite üzerinde kalıcı yerel veri saklama
- Değiştirilebilir tek genel hatırlatma saati (varsayılan `15:00`)
- Ertesi günün açık görevleri için özel hatırlatma penceresi
- Açık kullanıcı onayı ve kalıcı 10 dakikalık erteleme
- Kaçırılmış hatırlatmayı sonraki başlangıçta gösterme
- Sistem tepsisinde arka planda çalışma
- Kullanıcıya özel Windows Startup kısayolu
- Kullanıcı başına tek çalışan uygulama örneği; ikinci açılış mevcut pencereyi öne getirir
- Boyutu sınırlı ve dönen teknik günlükler
- SQLite'ın güvenli çevrimiçi yedekleme mekanizmasıyla elle yedek oluşturma

## Gereksinimler

- Windows 10 veya Windows 11
- Python 3.10 veya üzeri
- PySide6 6.8.3 (desteklenen aralık: `>=6.8.3,<6.9`)

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

## Windows EXE üretimi

Paketleme bağımlılıkları çalışma zamanı bağımlılıklarından ayrı tutulur:

```powershell
pip install -r requirements-build.txt
.\build_exe.ps1
```

Farklı bir Python çalıştırıcısı kullanılacaksa:

```powershell
.\build_exe.ps1 -Python "C:\Python\python.exe"
```

Tek dosyalık, terminal penceresi açmayan çıktı `dist\Hatirlatici.exe` konumunda
oluşur. EXE'yi çalıştırmak için hedef bilgisayarda Python veya PySide6 kurulması
gerekmez. `build/`, `dist/` ve PyInstaller'ın oluşturduğu `.spec` dosyaları Git'e
alınmaz; aynı betikle tekrar üretilebilir.

Paketleme betiği, PySide6 DLL dizinini Windows yükleme sırasına güvenli şekilde
ekleyen proje içi `pyi_runtime_hook.py` kancasını otomatik kullanır.

## Yerel veri konumu

Görevler, ayarlar ve günlük hatırlatma kayıtları aşağıdaki kullanıcıya özel
konumda saklanır:

```text
%LOCALAPPDATA%\Hatirlatici\hatirlatici.db
```

Bu veritabanı proje klasöründe değildir ve Git'e eklenmez.

Teknik uygulama günlükleri aşağıdaki klasörde tutulur:

```text
%LOCALAPPDATA%\Hatirlatici\logs
```

Günlükler görev başlığı veya açıklaması içermez; yalnızca başlangıç, kapanış,
hatırlatma ve hata türü gibi teknik olayları kaydeder. Dosya başına boyut
sınırı vardır ve en fazla üç eski günlük korunur.

## Veritabanı yedeği

Ayarlar ekranındaki **Veritabanını Yedekle** düğmesi, SQLite'ın çevrimiçi
yedekleme API'sini kullanarak tutarlı bir kopyayı şu klasöre yazar:

```text
%LOCALAPPDATA%\Hatirlatici\backups
```

Uygulama otomatik geri yükleme yapmaz. Geri yükleme gerekirse uygulama tamamen
kapatılmalı ve mevcut veritabanı korunarak işlem uzman denetiminde yapılmalıdır.

EXE kendi klasörüne kullanıcı verisi yazmaz ve normal kullanıcı yetkileriyle
çalışır; yönetici veya UAC yükseltmesi istemez.

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

Kaynak koddan çalıştırıldığında kısayol `pythonw.exe` ve `app.py` dosyasını;
paketlenmiş sürümden çalıştırıldığında doğrudan mevcut `Hatirlatici.exe` dosyasını
`--startup` argümanıyla hedefler.

Kurumsal bilgisayarlardaki Defender, SmartScreen, AppLocker veya kurum
politikaları imzasız yerel EXE'leri engelleyebilir. Uygulama bu güvenlik
mekanizmalarını aşmaya veya değiştirmeye çalışmaz.

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
Uygulama zaten çalışırken yeniden başlatılırsa ikinci kopya açılmaz; çalışan
örneğin ana penceresi öne getirilir.

## Güncelleme

Yeni sürüme geçmeden önce Ayarlar ekranından veritabanı yedeği alın. Sistem
tepsisi menüsünden uygulamayı tamamen kapatın, yeni `Hatirlatici.exe` dosyasını
kalıcı bir klasöre koyun ve çalıştırın. Windows ile başlat seçeneği etkinse yeni
EXE konumunu kullanması için ayarı kapatıp yeniden açın. Kullanıcı veritabanı EXE
dışında `%LOCALAPPDATA%` altında tutulduğu için normal güncellemede korunur.

## Henüz eklenmeyen özellikler

- Installer
- GitHub Release üzerinden dağıtım ve otomatik güncelleme
- Otomatik güncelleme
- Ağ, bulut ve çok kullanıcılı çalışma
- Outlook veya Google entegrasyonu
- Excel ve yapay zekâ özellikleri
- Tema sistemi
- Görev başına ayrı veya birden fazla genel hatırlatma saati
