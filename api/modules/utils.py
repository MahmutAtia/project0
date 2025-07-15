from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from fastapi import HTTPException, Header
from typing import Optional
import httpx
import os

DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")

clean_yaml_parser = StrOutputParser() | RunnableLambda(
    lambda x: x.replace("yaml", "").replace("yml", "").replace("```", "").strip()
)




async def verify_user_and_limits(feature: str, authorization: Optional[str] = Header(None)):
    """Call Django service to verify user and check limits for a specific feature"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")

    async with httpx.AsyncClient() as client:
        try:
            # Call Django API to verify token and check limits
            response = await client.get(
                f"{DJANGO_API_URL}/accounts/verify-and-check-limits/",
                headers={"Authorization": authorization},
                params={"feature": feature},
            )

            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid token")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Feature limit exceeded")
            elif response.status_code != 200:
                raise HTTPException(status_code=500, detail="Auth service error")

            return response.json()  # Returns user info and limits

        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Cannot reach auth service")

# Dependency factory function
def create_auth_dependency(feature_name: str):
    """Factory function to create feature-specific auth dependencies"""
    async def verify_auth(authorization: str = Header(...)):
        auth_data = await verify_user_and_limits(feature_name, authorization)
        # Include authorization in the returned data for convenience
        auth_data["authorization"] = authorization
        return auth_data
    return verify_auth
