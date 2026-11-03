let html5QrCode = null;
let isProcessing = false;

const readerContainer = document.getElementById('reader-container');
const readerDiv = document.getElementById('reader');
const resultCard = document.getElementById('result-card');
const resultText = document.getElementById('result-text');

async function checkCrueltyFree(barcode) {
    resultCard.style.display = "block";
    // Czyścimy klasy statusów przed nowym wyszukiwaniem
    resultCard.className = "";
    resultText.innerText = `Wykryto kod: ${barcode}\nSprawdzanie w bazie...`;

    try {
        const response = await fetch(`/api/product/${barcode}`);
        
        if (!response.ok) throw new Error(`Błąd HTTP: ${response.status}`);
        const data = await response.json();
        
        let brandText = (data.brand && data.brand !== "Nieznana") ? data.brand : "";

        if (data.cruelty_free === true) {
            resultCard.classList.add("status-cruelty-free");
            resultText.innerText = brandText ? `Marka: ${brandText}\n\nCruelty free` : `Cruelty free`;
        } else if (data.cruelty_free === false) {
            resultCard.classList.add("status-testing");
            resultText.innerText = brandText ? `Marka: ${brandText}\n\nTestuje na zwierzętach` : `Testuje na zwierzętach`;
        } else if (brandText) {
            // Sytuacja, gdy marka jest znana, ale brakuje danych o statusie w API
            resultText.innerText = `Marka: ${brandText}\n\nBrak danych o testowaniu`;
        } else {
            resultText.innerText = `Kod: ${barcode}\nNie znaleziono produktu w bazie\nOpen Beauty/Food Facts.`;
        }
    } catch (error) {
        console.error("Błąd API:", error);
        resultCard.classList.add("status-testing"); // Używamy czerwonego koloru dla błędu
        resultText.innerText = "Błąd połączenia z serwerem API.\nSprawdź czy FastAPI działa.";
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

    // 2. Pokazujemy CAŁY kontener w DOM ZANIM zainicjalizujemy kamerę
    resultCard.style.display = "none";
    readerContainer.style.display = "block";
    resultCard.className = ""; // Reset klas przy restarcie

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

            // Po pomyślnym skanie całkowicie wyłączamy strumień i ukrywamy CAŁY kontener
            await stopAndClearScanner();
            readerContainer.style.display = "none";
            checkCrueltyFree(decodedText);
        },
        (errorMessage) => {}
    ).catch(async (err) => {
        console.error("Błąd startu kamery:", err);
        await stopAndClearScanner();
        resultCard.style.display = "block";
        // W razie błędu również ukrywamy CAŁY kontener
        readerContainer.style.display = "none";
        resultCard.classList.add("status-testing"); // Czerwony kolor dla błędu
        resultText.innerText = "Błąd aparatu.\nUdziel aplikacji dostępu do kamery lub zrestartuj skanowanie.";
    });
}

window.onload = startScanner;