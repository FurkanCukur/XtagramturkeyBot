# Türkiye Gündem Botu

RSS haberlerini ve X (Twitter) trendlerini takip edip önemli olanları
Telegram'a bildiren basit bir bot. Amaç: sana "şurada bir şey oluyor"
diye haber vermek, içeriği Instagram'a taşıma işini sen yapıyorsun.

Tüm sistem ücretsiz çalışacak şekilde tasarlandı (GitHub Actions +
Telegram Bot API, ikisi de bedava).

## 1. Telegram botu oluştur

1. Telegram'da **@BotFather** hesabına yaz.
2. `/newbot` komutunu gönder, bot için bir isim ve kullanıcı adı belirle.
3. BotFather sana bir **token** verecek (şuna benzer:
   `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`). Bunu not al —
   bu senin `TELEGRAM_BOT_TOKEN` değerin.

## 2. Kendi chat_id'ini öğren

1. Telegram'da yeni oluşturduğun botu bul ve ona herhangi bir mesaj
   (örn. "merhaba") gönder.
2. Tarayıcında şu adresi aç (TOKEN yerine kendi token'ını yaz):
   `https://api.telegram.org/botTOKEN/getUpdates`
3. Çıkan JSON içinde `"chat":{"id": 123456789, ...}` şeklinde bir
   alan göreceksin. Buradaki sayı senin `TELEGRAM_CHAT_ID` değerin.

## 3. Projeyi GitHub'a yükle

1. GitHub'da yeni, **private** bir repo oluştur.
2. Bu klasördeki tüm dosyaları (main.py, requirements.txt, state.json,
   .github/ klasörü) o repoya yükle.

## 4. Token ve chat_id'i GitHub'a "secret" olarak ekle

1. Repo sayfasında **Settings > Secrets and variables > Actions**'a git.
2. "New repository secret" ile iki secret ekle:
   - `TELEGRAM_BOT_TOKEN` → BotFather'dan aldığın token
   - `TELEGRAM_CHAT_ID` → 2. adımda bulduğun sayı

Token'ı asla kod içine yazma / repoya çıplak halde koyma — secret
olarak eklemenin sebebi bu.

## 5. Botu test et

1. Repo sayfasında **Actions** sekmesine git.
2. "Gündem Botu" workflow'unu seç, sağdaki **Run workflow** butonuna
   bas (elle tetikleme).
3. Çalışma bitince Telegram'ına bildirim gelip gelmediğini kontrol et.
4. Bundan sonra otomatik olarak her 10 dakikada bir kendiliğinden
   çalışacak.

## Ayarları değiştirmek istersen

`main.py` dosyasının başındaki **AYARLAR** bölümünden şunları
değiştirebilirsin:

- `RSS_KAYNAKLARI` — takip edilen haber siteleri
- `MIN_KAYNAK_SAYISI` — bir haberin "önemli" sayılması için en az
  kaç farklı kaynakta geçmesi gerektiği
- `ONEMLI_KELIMELER` — başlıkta geçtiğinde otomatik önemli sayılacak
  kelimeler

## Bilinmesi gerekenler / sınırlamalar

- **RSS adresleri değişebilir.** `RSS_KAYNAKLARI` içindeki URL'leri
  kullanmadan önce tarayıcında açıp gerçekten çalıştığını doğrula.
  Haber siteleri zaman zaman feed adreslerini değiştiriyor; bir kaynak
  çalışmazsa terminal/Actions log'unda hata mesajı görürsün, o kaynağı
  güncelleyip düzeltebilirsin.
- **trends24.in taraması kırılgan.** Bu, resmi bir API değil, herkese
  açık bir web sayfasının HTML'ini okuyor (scraping). Site tasarımını
  değiştirirse `guncel_trendleri_cek()` fonksiyonundaki CSS seçicisini
  güncellemen gerekebilir (tarayıcıda F12 > Elements ile trend
  listesinin hangi etiket/class içinde olduğuna bakabilirsin).
- Bu yöntem gerçek tweet metnini/linkini getirmiyor, sadece "şu konu
  trend oluyor" ya da "şu haber birden fazla kaynakta çıktı" sinyalini
  veriyor. Asıl tweet'i bulup içerik haline getirme işini hâlâ sen
  yapıyorsun — botun amacı bu aramayı senin için tetiklemek.
