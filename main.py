"""
Türkiye Gündem Botu
--------------------
Bu script periyodik olarak (örn. her 10 dakikada bir) çalışır ve:

1) Birden fazla Türk haber sitesinin RSS akışını tarar. Aynı konu kısa
   sürede birden fazla farklı kaynakta çıkarsa ya da başlıkta "önemli"
   sayılan bir kelime geçerse, bunu Telegram'a bildirir.
2) trends24.in/turkey sayfasından güncel Twitter/X trendlerini çeker,
   daha önce görmediğin yeni bir trend çıkarsa bildirir.

Aynı haberi/trendi tekrar tekrar bildirmemek için basit bir "state"
(durum) dosyası (state.json) kullanılır. Bu dosya her çalıştırmada
güncellenir.

Ortam değişkenleri (environment variables) olarak şunlar gerekiyor:
  TELEGRAM_BOT_TOKEN  -> BotFather'dan aldığın token
  TELEGRAM_CHAT_ID    -> Bildirimlerin gideceği sohbetin id'si
"""

import os
import json
import hashlib

import requests
import feedparser
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# AYARLAR — projeyi kendine göre uyarlamak istersen burayı değiştir
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

# ÖNEMLİ: Bu URL'leri kullanmadan önce tarayıcında açıp gerçekten
# çalıştığını doğrula. Haber siteleri zaman zaman RSS adreslerini
# değiştirebiliyor. Kendi bulduğun/doğruladığın kaynakları da
# buraya ekleyebilirsin.
RSS_KAYNAKLARI = {
    "AA": "https://www.aa.com.tr/tr/rss/default?cat=guncel",
    "NTV": "https://www.ntv.com.tr/gundem.rss",
    "Hurriyet": "https://www.hurriyet.com.tr/rss/gundem",
    "Sozcu": "https://www.sozcu.com.tr/rss/gundem.xml",
    "CNNTurk": "https://www.cnnturk.com/feed/rss/turkiye/news",
}

# Bir haber, en az bu kadar farklı kaynakta geçerse "önemli" sayılır
MIN_KAYNAK_SAYISI = 2

# Başlıkta geçtiğinde otomatik önemli sayılacak kelimeler
# (kendi ilgi alanına göre serbestçe genişlet/daralt)
ONEMLI_KELIMELER = [
    "deprem", "istifa", "patlama", "yangın", "saldırı", "kaza",
    "zam", "seçim", "grev", "iflas", "afet", "kriz", "operasyon",
]

# Twitter/X Türkiye trendlerini gösteren herkese açık sayfa.
# NOT: Bu bir "scraping" işlemi, sitenin HTML yapısı değişirse
# aşağıdaki CSS seçicisinin de güncellenmesi gerekebilir.
TRENDS24_URL = "https://trends24.in/turkey/"

# Başlıkların "aynı haber" sayılması için benzerlik eşiği (0-100)
BASLIK_BENZERLIK_ESIGI = 75


# ---------------------------------------------------------------------------
# STATE (daha önce bildirilenleri hatırlama)
# ---------------------------------------------------------------------------

def state_yukle():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"gonderilen_haberler": [], "bilinen_trendler": []}


def state_kaydet(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# TELEGRAM
# ---------------------------------------------------------------------------

def telegram_mesaj_gonder(metin):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("UYARI: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID tanımlı değil, "
              "mesaj gönderilmiyor. Mesaj:")
        print(metin)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": metin,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, data=payload, timeout=15)
        if not r.ok:
            print("Telegram gönderim hatası:", r.text)
    except requests.RequestException as e:
        print("Telegram isteği başarısız:", e)


# ---------------------------------------------------------------------------
# RSS HABER TOPLAMA VE ÖNEMLİLİK TESPİTİ
# ---------------------------------------------------------------------------

def rss_haberleri_topla():
    tum_haberler = []
    for kaynak_adi, url in RSS_KAYNAKLARI.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                baslik = entry.get("title", "").strip()
                link = entry.get("link", "")
                if baslik:
                    tum_haberler.append({
                        "kaynak": kaynak_adi,
                        "baslik": baslik,
                        "link": link,
                    })
        except Exception as e:
            print(f"[{kaynak_adi}] RSS okunamadı: {e}")
    return tum_haberler


def basliklar_benzer_mi(b1, b2):
    return fuzz.token_sort_ratio(b1, b2) >= BASLIK_BENZERLIK_ESIGI


def onemli_haberleri_bul(haberler):
    """
    Aynı haberi farklı kaynaklarda gruplar. Bir grup, yeterince
    kaynakta geçiyorsa ya da önemli bir kelime içeriyorsa "önemli"
    listesine eklenir.
    """
    gruplar = []  # her biri: {"baslik", "kaynaklar": set(), "link"}

    for haber in haberler:
        eslesen_grup = None
        for grup in gruplar:
            if basliklar_benzer_mi(haber["baslik"], grup["baslik"]):
                eslesen_grup = grup
                break

        if eslesen_grup:
            eslesen_grup["kaynaklar"].add(haber["kaynak"])
        else:
            gruplar.append({
                "baslik": haber["baslik"],
                "kaynaklar": {haber["kaynak"]},
                "link": haber["link"],
            })

    onemli = []
    for grup in gruplar:
        baslik_kucuk = grup["baslik"].lower()
        kelime_eslesti = any(k in baslik_kucuk for k in ONEMLI_KELIMELER)
        if len(grup["kaynaklar"]) >= MIN_KAYNAK_SAYISI or kelime_eslesti:
            onemli.append(grup)
    return onemli


def haber_id_uret(baslik):
    # Başlığı küçük harfe çevirip hash'liyoruz ki aynı haberi
    # tekrar tekrar bildirmeyelim.
    return hashlib.sha1(baslik.strip().lower().encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# TWITTER/X TREND TAKİBİ (trends24.in üzerinden)
# ---------------------------------------------------------------------------

def guncel_trendleri_cek():
    try:
        r = requests.get(
            TRENDS24_URL,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (gundem-botu)"},
        )
        r.raise_for_status()
    except requests.RequestException as e:
        print("trends24.in adresine ulaşılamadı:", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    # trends24.in genelde ilk sütunda "şu anki" trendleri gösterir.
    # Site HTML yapısını değiştirirse bu seçici de güncellenmelidir
    # (tarayıcıda F12 > Elements ile kontrol edebilirsin).
    ilk_liste = soup.select_one("ol.trend-card__list")
    if ilk_liste is None:
        print("UYARI: trends24.in HTML yapısı değişmiş olabilir, "
              "trend listesi bulunamadı.")
        return []

    trendler = [a.get_text(strip=True) for a in ilk_liste.select("a")]
    return trendler[:10]


# ---------------------------------------------------------------------------
# ANA AKIŞ
# ---------------------------------------------------------------------------

def calistir():
    state = state_yukle()
    gonderilen_haberler = set(state.get("gonderilen_haberler", []))
    bilinen_trendler = set(state.get("bilinen_trendler", []))

    # 1) RSS haberlerini kontrol et
    haberler = rss_haberleri_topla()
    onemli_haberler = onemli_haberleri_bul(haberler)

    for grup in onemli_haberler:
        hid = haber_id_uret(grup["baslik"])
        if hid in gonderilen_haberler:
            continue

        kaynak_metni = ", ".join(sorted(grup["kaynaklar"]))
        mesaj = (
            f"📰 <b>{grup['baslik']}</b>\n"
            f"Kaynak(lar): {kaynak_metni}\n"
            f"{grup['link']}"
        )
        telegram_mesaj_gonder(mesaj)
        gonderilen_haberler.add(hid)

    # 2) Twitter/X trendlerini kontrol et
    guncel_trendler = guncel_trendleri_cek()
    for trend in guncel_trendler:
        if trend and trend not in bilinen_trendler:
            telegram_mesaj_gonder(
                f"🔥 Yeni trend (X/Twitter Türkiye): <b>{trend}</b>"
            )
            bilinen_trendler.add(trend)

    # State dosyası sonsuza kadar büyümesin diye son N kaydı tutuyoruz
    state["gonderilen_haberler"] = list(gonderilen_haberler)[-500:]
    state["bilinen_trendler"] = list(bilinen_trendler)[-100:]
    state_kaydet(state)

    print(
        f"Bitti: {len(onemli_haberler)} önemli haber grubu incelendi, "
        f"{len(guncel_trendler)} trend kontrol edildi."
    )


if __name__ == "__main__":
    calistir()
