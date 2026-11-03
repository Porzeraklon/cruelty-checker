let html5QrCode = null;
let isProcessing = false;

const readerDiv = document.getElementById('reader');
const resultCard = document.getElementById('result-card');
const resultText = document.getElementById('result-text');

async function checkCrueltyFree(barcode) {
    resultCard.style.display = "block";
    resultText.innerText = `Wykryto kod: ${barcode}\nSprawdzanie w bazie...`;
    resultText.style.color = "#333";

    try {
        const response = await fetch(`/api/product/${barcode}`);
        
        if (!response.ok) throw new Error(`Błąd HTTP: ${response.status}`);
        const data = await response.json();
        
        let productHeader = "";
        if (data.brand && data.brand !== "Nieznana") {
            productHeader = `Marka: ${data.brand}\n`;
            if (data.product_name) {
                productHeader += `„${data.product_name}”\n\n`;
            }
        }

        if (data.cruelty_free === true) {
            resultText.innerText = `${productHeader}🐇 Wolne od okrucieństwa!`;
            resultText.style.color = "#16a34a";
        } else if (data.cruelty_free === false) {
            resultText.innerText = `${productHeader}🧪 Testuje na zwierzętach`;
            resultText.style.color = "#dc2626";
        } else if (data.brand && data.brand !== "Nieznana") {
            resultText.innerText = `${productHeader}❓ Brak danych o testowaniu tej marki w naszej bazie.`;
            resultText.style.color = "#d97706";
        } else {
            resultText.innerText = `Kod: ${barcode}\nNie znaleziono produktu w bazie Open Beauty/Food Facts.`;
            resultText.style.color = "#4b5563";
        }
    } catch (error) {
        console.error("Błąd API:", error);
        resultText.innerText = "Błąd połączenia z serwerem API.\nSprawdź czy FastAPI działa.";
        resultText.style.color = "#ea580c";
    }
}

async function stopAndClearScanner() {
    if (html5QrCode) {
        try {
            if (html5QrCode.isScanning) {
                await html5QrCode.stop();
            }
            await html5QrCode.clear();
        } catch (err) {
            console.warn("Czyszczenie skanera:", err);
        }
        html5QrCode = null;
    }
}

async function startScanner() {
    isProcessing = false;
    
    // 1. Najpierw czyścimy ewentualny stary strumień i obiekty
    await stopAndClearScanner();

    // 2. Pokazujemy element w DOM ZANIM zainicjalizujemy kamerę (wymóg WebView)
    resultCard.style.display = "none";
    readerDiv.style.display = "block";

    // 3. Tworzymy świeżą instancję skanera
    html5QrCode = new Html5Qrcode("reader");

    const config = { 
        fps: 10,
        formatsToSupport: [ 
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8 
        ]
    };

    html5QrCode.start(
        { facingMode: "environment" },
        config,
        async (decodedText) => {
            if (isProcessing) return;
            isProcessing = true;

            // Po pomyślnym skanie całkowicie wyłączamy strumień i czyścimy DOM
            await stopAndClearScanner();
            readerDiv.style.display = "none";
            checkCrueltyFree(decodedText);
        },
        (errorMessage) => {}
    ).catch(async (err) => {
        console.error("Błąd startu kamery:", err);
        await stopAndClearScanner();
        resultCard.style.display = "block";
        readerDiv.style.display = "none";
        resultText.innerText = "Błąd aparatu.\nUdziel aplikacji dostępu do kamery lub zrestartuj skanowanie.";
        resultText.style.color = "#dc2626";
    });
}

window.onload = startScanner;