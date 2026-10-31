"""
FastAPI application entry point for Supplier Acknowledgement and Schedule Impact Manager.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database import init_db, check_database_connection, SessionLocal
from backend.routes import router
from backend import models, services

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Safe application lifecycle startup and shutdown handler."""
    print("[Startup] Checking MySQL database connectivity...")
    db_ok = check_database_connection()
    if db_ok:
        print("[Startup] MySQL is reachable. Performing safe schema verification...")
        init_db(safe_only=True)

        # Check if database has data; if completely empty, perform initial seed
        db = SessionLocal()
        try:
            po_count = db.query(models.PurchaseOrder).count()
            if po_count == 0:
                default_scale = settings.dataset_scale.lower().strip()
                print(f"[Startup] Database is empty. Performing initial deterministic seed ({default_scale} scale)...")
                services.seed_database_from_generator(scale=default_scale)
                print(f"[Startup] Initial baseline seed completed successfully ({default_scale} scale).")
            else:
                print(f"[Startup] Found {po_count} existing purchase orders. Preserving database state across restarts.")
        except Exception as exc:
            print(f"[Startup Warning] Could not inspect/seed initial data: {exc}")
        finally:
            db.close()
    else:
        print("[Startup Warning] MySQL server is not reachable. Ensure MySQL is running on localhost:3306.")

    yield
    print("[Shutdown] Application shutdown complete.")


app = FastAPI(
    title="Supplier Acknowledgement and Schedule Impact Manager",
    description="Enterprise API managing supplier acknowledgements, change requests, approvals, projected supply, and downstream schedule impacts.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS from validated settings (ADR-0001 D4)
cors_origins = settings.cors_origin_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router)


@app.get("/health")
def health_check():
    db_connected = check_database_connection()
    return {
        "status": "healthy" if db_connected else "degraded",
        "database_connected": db_connected,
        "service": "Supplier Acknowledgement and Schedule Impact Manager"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )

