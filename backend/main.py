import json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
import httpx

# --- 1. Konfiguracja bazy danych SQLite w podmontowanym katalogu /app/data ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/cruelty_free.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. Modele tabel ---
class Brand(Base):
    """Tabela ze statusami marek (cruelty_free: True/False)"""
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    cruelty_free = Column(Boolean, nullable=False)

class ProductCache(Base):
    """Tabela podręczna przechowująca dopasowania kodów EAN do marek i nazw produktów"""
    __tablename__ = "products_cache"
    barcode = Column(String, primary_key=True, index=True)
    brand_name = Column(String)
    product_name = Column(String)

# --- 3. Funkcja seedująca z pliku brands.json ---
def seed_db():
    """Tworzy tabele i zasila bazę danymi z pliku brands.json przy starcie"""
    Base.metadata.create_all(bind=engine)
    
    json_path = Path(__file__).parent / "brands.json"
    if not json_path.exists():
        print("Uwaga: Brak pliku brands.json! Pomijam wstępne seedowanie.")
        return

    db = SessionLocal()
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            brands_data = json.load(f)

        for brand_item in brands_data:
            existing = db.query(Brand).filter(Brand.name.ilike(brand_item["name"])).first()
            if not existing:
                db.add(Brand(name=brand_item["name"].title(), cruelty_free=brand_item["cruelty_free"]))
        
        db.commit()
        print(f"Baza danych pomyślnie zasilona z pliku {json_path.name}")
    except Exception as e:
        print(f"Błąd podczas ładowania brands.json: {e}")
    finally:
        db.close()

# --- 4. Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_db()
    yield

# --- 5. Inicjalizacja FastAPI ---
app = FastAPI(title="Cruelty Free API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class BrandCreate(BaseModel):
    name: str
    cruelty_free: bool

# --- 6. Pobieranie danych z zewnętrznych API (OBF -> OFF) ---
async def fetch_data_from_apis(barcode: str) -> dict | None:
    api_urls = [
        f"https://world.openbeautyfacts.org/api/v0/product/{barcode}.json",
        f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    ]
    
    async with httpx.AsyncClient() as client:
        for url in api_urls:
            try:
                response = await client.get(url, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == 1:
                        product_data = data.get("product", {})
                        
                        brands_raw = product_data.get("brands", "")
                        if not brands_raw:
                            brands_tags = product_data.get("brands_tags", [])
                            brands_raw = brands_tags[0] if brands_tags else ""
                            
                        product_name = (
                            product_data.get("product_name_pl") 
                            or product_data.get("product_name") 
                            or "Nieznany produkt"
                        )
                        
                        if brands_raw:
                            brand_clean = brands_raw.split(",")[0].strip().title()
                            return {
                                "brand": brand_clean,
                                "name": product_name
                            }
            except httpx.RequestError as exc:
                print(f"Błąd połączenia z {url}: {exc}")
                continue
                
    return None

# --- 7. Endpointy ---
@app.get("/api/product/{barcode}")
async def check_product(barcode: str, db: Session = Depends(get_db)):
    cached = db.query(ProductCache).filter(ProductCache.barcode == barcode).first()
    
    if cached:
        brand_name = cached.brand_name
        product_name = cached.product_name
    else:
        api_result = await fetch_data_from_apis(barcode)
        
        if api_result:
            brand_name = api_result["brand"]
            product_name = api_result["name"]
            
            new_cache = ProductCache(
                barcode=barcode, 
                brand_name=brand_name,
                product_name=product_name
            )
            db.add(new_cache)
            db.commit()
        else:
            return {
                "barcode": barcode,
                "brand": "Nieznana", 
                "product_name": None,
                "cruelty_free": None,
                "message": "Nie znaleziono produktu w zewnętrznych API."
            }
        
    db_brand = db.query(Brand).filter(Brand.name.ilike(f"%{brand_name}%")).first()
    
    return {
        "barcode": barcode,
        "brand": brand_name, 
        "product_name": product_name,
        "cruelty_free": db_brand.cruelty_free if db_brand else None
    }

@app.post("/api/brands")
def create_brand(brand: BrandCreate, db: Session = Depends(get_db)):
    db_brand = db.query(Brand).filter(Brand.name.ilike(brand.name)).first()
    if db_brand:
        raise HTTPException(status_code=400, detail="Marka już istnieje w bazie.")
    
    new_brand = Brand(name=brand.name.title(), cruelty_free=brand.cruelty_free)
    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)
    return new_brand

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    true_count = db.query(Brand).filter(Brand.cruelty_free == True).count()
    false_count = db.query(Brand).filter(Brand.cruelty_free == False).count()
    
    return {
        "true_count": true_count, 
        "false_count": false_count
    }