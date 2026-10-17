from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.db.session import Base, engine
from app import models
from app.routers import auth, users , categories , products , inventory , suppliers , orders , purchase_orders


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.APP_NAME,
    description="E-Commerce & Inventory Management Backend API",
    version="1.0.0",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(suppliers.router)
app.include_router(orders.router)
app.include_router(purchase_orders.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}