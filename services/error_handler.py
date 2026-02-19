from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback


SAFE_ERROR_MESSAGES = {
    400: "Requête invalide",
    401: "Authentification requise",
    403: "Accès refusé",
    404: "Ressource non trouvée",
    405: "Méthode non autorisée",
    422: "Données invalides",
    500: "Erreur interne du serveur",
}


def sanitize_error_message(status_code: int, detail: str = "") -> str:
    if status_code < 500 and detail:
        safe_keywords = ["mot de passe", "authentification", "non trouvé",
                         "invalide", "requis", "incorrect", "manquant",
                         "password", "required", "not found"]
        detail_lower = detail.lower()
        if any(kw in detail_lower for kw in safe_keywords):
            return detail
    return SAFE_ERROR_MESSAGES.get(status_code, "Erreur inattendue")


async def generic_exception_handler(request: Request, exc: Exception):
    print(f"❌ Unhandled exception on {request.method} {request.url.path}: {exc}", flush=True)
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": SAFE_ERROR_MESSAGES[500]}
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    safe_message = sanitize_error_message(exc.status_code, exc.detail)
    if exc.status_code >= 500:
        print(f"❌ HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}", flush=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": safe_message}
    )
