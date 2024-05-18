from fastapi import FastAPI, HTTPException, Query, Request, Form 
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from passlib.context import CryptContext
import httpx

MONGO_URI = "mongodb+srv://Brinsu:6ZcYs5bXgggwSPvL@cluster5.d5i0f3a.mongodb.net/"

DATABASE_NAME = "user_db"

app = FastAPI()
templates = Jinja2Templates(directory="templates")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
users_collection = db["users"]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

Url = "https://api.metalpriceapi.com/v1"
Key = "af38e20778a4467188ab5377709ef17d"

supported_metals = ["XAU", "XAG", "XPT", "XPD"]

@app.get("/")
async def show_register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = users_collection.find_one({"username": username})
    if user:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_password = hash_password(password)
    user_id = users_collection.insert_one({"username": username, "password": hashed_password}).inserted_id
    return templates.TemplateResponse("register_success.html", {"request": request, "username": username})

@app.get("/login")
async def show_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = users_collection.find_one({"username": username})
    if user is None or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return templates.TemplateResponse("index.html", {"request": request, "username": username})

@app.get("/home")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/metals")
async def show_form(request: Request):
    return templates.TemplateResponse("metalform.html", {"request": request, "metals": supported_metals})

@app.post("/metals")
async def get_metal_price(request: Request, metal: str = Form(...), amount: float = Form(...), currencies: str = Form(None)):
    if metal not in supported_metals:
        raise HTTPException(status_code=404, detail="Metal not supported")

    currency_list = currencies.split(",") if currencies else ["USD"]

    metal_prices = []
    for currency in currency_list:
        params = {"api_key": Key, "base": currency, "symbols": metal}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{Url}/latest", params=params)
            data = response.json()

        metal_price = data["rates"][metal]
        total_price = metal_price * amount
        metal_prices.append({"currency": currency, "price_per_unit": metal_price, "total_price": total_price})

    return templates.TemplateResponse("metalresults.html", {"request": request, "metal": metal, "amount": amount, "prices": metal_prices})

@app.get("/latest")
async def get_latest_rates(request: Request, base: str = Query(None)):
    params = {"api_key": Key}
    if base:
        params["base"] = base

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{Url}/latest", params=params)
        data = response.json()

    return templates.TemplateResponse("latest.html", {"request": request, "data": data})

@app.get("/historical")
async def show_historical_form(request: Request):
    return templates.TemplateResponse("historicalform.html", {"request": request})

@app.post("/historical")
async def get_historical_rates(request: Request, date: str = Form(...)):
    params = {"api_key": Key}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{Url}/{date}", params=params)
        data = response.json()

    return templates.TemplateResponse("historicalresults.html", {"request": request, "date": date, "data": data})

@app.get("/convert")
async def show_conversion_form(request: Request):
    return templates.TemplateResponse("conversionform.html", {"request": request})

@app.post("/convert")
async def perform_currency_conversion(request: Request, source_currency: str = Form(...), target_currency: str = Form(...), amount: float = Form(...)):
    params = {"api_key": Key, "base": source_currency, "symbols": target_currency}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{Url}/latest", params=params)
        data = response.json()

    if target_currency in data["rates"]:
        exchange_rate = data["rates"][target_currency]
        converted_amount = amount * exchange_rate
        return templates.TemplateResponse("conversionresults.html", {"request": request, "source_currency": source_currency, "target_currency": target_currency, "amount": amount, "converted_amount": converted_amount})
    else:
        raise HTTPException(status_code=404, detail=f"Conversion rate from {source_currency} to {target_currency} not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)