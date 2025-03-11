from fastapi import Security, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth0.utils import VerifyToken
from routers import files, chats, rag, analytics

origins = [
    "http://localhost",
    "http://localhost:3000",
]

auth = VerifyToken()
app = FastAPI()

# Add cors settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router)
app.include_router(chats.router)
app.include_router(rag.router)
app.include_router(analytics.router, prefix="/analytics")
