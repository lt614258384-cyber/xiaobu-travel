import os
import uvicorn

if __name__ == "__main__":
    is_prod = os.getenv("ENV", "").lower() == "production"
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=not is_prod,
    )
