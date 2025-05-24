from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api.routers import (
    auth,
    bidders,
    comparison,
    initialization,
    multiplication,
    reconstruction,
    redistribution,
    reset,
    shares,
    xor,
)

app = FastAPI(
    title="Secure Multi-Party Computation API",
    version="1.0.0",
    description="API for performing secure multi-party computation protocols.",
    openapi_tags=[
        {
            "name": "Status",
            "description": "Endpoints for checking the server status.",
        },
        {
            "name": "Initialization",
            "description": "Endpoints for setting up the initial parameters of the MPC protocol.",
        },
        {
            "name": "Shares",
            "description": "Endpoints for managing and setting client shares.",
        },
        {
            "name": "Comparison",
            "description": "Endpoints for performing secure comparison protocols.",
        },
        {
            "name": "Redistribution",
            "description": "Endpoints for redistributing intermediate values (q and r).",
        },
        {
            "name": "Multiplication",
            "description": "Endpoints for secure multiplication steps.",
        },
        {
            "name": "XOR",
            "description": "Endpoint for secure XOR operation.",
        },
        {
            "name": "Reconstruction",
            "description": "Endpoint for reconstructing the final secret or comparison result.",
        },
        {
            "name": "Reset",
            "description": "Endpoints for resetting the server state.",
        },
        {
            "name": "Authentication",
            "description": "Endpoints for user registration and login.",
        },
        {
            "name": "Bidders",
            "description": "Endpoints for retrieving information about bidders",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(initialization.router)
app.include_router(shares.router)
app.include_router(comparison.router)
app.include_router(redistribution.router)
app.include_router(multiplication.router)
app.include_router(xor.router)
app.include_router(reconstruction.router)
app.include_router(reset.router)
app.include_router(bidders.router)
